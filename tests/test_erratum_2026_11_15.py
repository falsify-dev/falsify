"""Regression tests for the PRML v0.1 erratum of 2026-11-15.

tests/fixtures/erratum-2026-11-15-cases.json holds one input per rule (YAML number
spellings, unquoted timestamps, non-finite numbers, seed range, structure, lone
surrogates, empty collections, ties, float spelling, the plain-scalar predicate for
`---`/`...`, long and empty keys, anchors). `canonical` is the expected byte
sequence, or null when the input MUST be rejected with exit code 2.

The Python reference is checked in-process. The JavaScript, Go and Rust CLIs are
checked through `hash` when their toolchain or binary is available (Go and Rust read
JSON only), matching the skip pattern of test_linkage_parity.py.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import falsify
import falsify_prml as fp

ROOT = Path(__file__).resolve().parent.parent
CASES = json.loads((ROOT / "tests" / "fixtures" / "erratum-2026-11-15-cases.json").read_text(encoding="utf-8"))["cases"]

_TMP = tempfile.mkdtemp(prefix="falsify-erratum-")
_GO = None


def _write(case) -> Path:
    p = Path(_TMP) / f"{case['id'].replace('/', '_')}.{case['format']}"
    p.write_text(case["input"], encoding="utf-8")
    return p


def _go_binary():
    global _GO
    if _GO is None:
        _GO = ""
        if shutil.which("go"):
            out = Path(_TMP) / "falsify-go"
            r = subprocess.run(["go", "build", "-o", str(out), "."], cwd=ROOT / "impl" / "go",
                               capture_output=True, text=True, timeout=180)
            if r.returncode == 0:
                _GO = str(out)
    return _GO or None


def _targets():
    t = {}
    node = shutil.which("node")
    if node:
        has_yaml = subprocess.run([node, "-e", "require.resolve('js-yaml')"], cwd=ROOT / "impl" / "js",
                                  capture_output=True).returncode == 0
        t["js"] = ([node, str(ROOT / "impl" / "js" / "falsify.js"), "hash"], ("json", "yaml") if has_yaml else ("json",))
    go = _go_binary()
    if go:
        t["go"] = ([go, "hash"], ("json",))
    rs = ROOT / "impl" / "rust" / "target" / "release" / "falsify-rs"
    if rs.exists():
        t["rust"] = ([str(rs), "hash"], ("json",))
    return t


class TestPythonReference(unittest.TestCase):
    def test_each_case(self):
        for case in CASES:
            with self.subTest(case=case["id"]):
                path = _write(case)
                try:
                    m = fp.load_manifest(str(path))
                    errs = fp.validate_manifest(m)
                    got = None if errs else fp.canonicalize(m)
                except ValueError:
                    got = None
                self.assertEqual(got, case["canonical"])

    def test_every_rule_has_an_accept_or_reject_case(self):
        self.assertGreaterEqual(sum(c["canonical"] is None for c in CASES), 10)
        self.assertGreaterEqual(sum(c["canonical"] is not None for c in CASES), 10)


class TestOtherImplementations(unittest.TestCase):
    def test_cli_hash_matches_reference(self):
        targets = _targets()
        # CI sets ERRATUM_REQUIRE (js, go or rust) so a failed build cannot turn into a skip.
        required = [n for n in os.environ.get("ERRATUM_REQUIRE", "").split(",") if n]
        missing = [n for n in required if n not in targets]
        self.assertFalse(missing, f"required implementation not available: {missing}")
        if not targets:
            raise unittest.SkipTest("no other implementation available (node/go/rust missing)")
        for name, (cmd, formats) in targets.items():
            for case in CASES:
                if case["format"] not in formats:
                    continue
                with self.subTest(impl=name, case=case["id"]):
                    r = subprocess.run(cmd + [str(_write(case))], capture_output=True, text=True, timeout=60)
                    if case["canonical"] is None:
                        self.assertEqual(r.returncode, 2, f"{name} accepted: {r.stdout.strip()}")
                    else:
                        self.assertEqual(r.returncode, 0, f"{name} rejected: {r.stderr.strip()[:200]}")
                        want = hashlib.sha256(case["canonical"].encode("utf-8")).hexdigest()
                        self.assertEqual(r.stdout.strip().splitlines()[-1], want)


class TestLockCreatedAt(unittest.TestCase):
    """Second part of the erratum: `lock` takes created_at only as YYYY-MM-DDTHH:MM:SSZ;
    `hash` keeps reading manifests locked earlier in another RFC 3339 spelling."""

    def _manifest(self, created_at):
        case = next(c for c in CASES if c["id"] == "E2-created-at-offset-reads")
        m = json.loads(case["input"])
        m["created_at"] = created_at
        p = Path(tempfile.mkdtemp(dir=_TMP)) / "claim.json"
        p.write_text(json.dumps(m), encoding="utf-8")
        return p

    def _clis(self):
        clis = [("python", [sys.executable, str(ROOT / "falsify_prml.py")])]
        if shutil.which("node"):
            clis.append(("js", [shutil.which("node"), str(ROOT / "impl" / "js" / "falsify.js")]))
        return clis

    def test_lock_refuses_other_spellings_hash_reads_them(self):
        for name, cli in self._clis():
            for spelling in ("2026-05-01T12:00:00+00:00", "2026-05-01T12:00:00.000Z", "2026-05-01t12:00:00z"):
                with self.subTest(impl=name, created_at=spelling):
                    p = self._manifest(spelling)
                    self.assertEqual(subprocess.run(cli + ["lock", str(p)], capture_output=True).returncode, 2)
                    self.assertEqual(subprocess.run(cli + ["hash", str(p)], capture_output=True).returncode, 0)
            with self.subTest(impl=name, created_at="canonical"):
                p = self._manifest("2026-05-01T12:00:00Z")
                self.assertEqual(subprocess.run(cli + ["lock", str(p)], capture_output=True).returncode, 0)


class TestLegacyCliDuplicateKeys(unittest.TestCase):
    def test_spec_loader_rejects_a_repeated_key(self):
        import yaml
        with self.assertRaises(yaml.YAMLError):
            falsify._load_spec_yaml("threshold: 0.90\nmetric: accuracy\nthreshold: 0.10\n")

    def test_spec_loader_reads_a_normal_spec(self):
        self.assertEqual(falsify._load_spec_yaml("threshold: 0.9\nmetric: accuracy\n"),
                         {"threshold": 0.9, "metric": "accuracy"})


if __name__ == "__main__":
    unittest.main()
