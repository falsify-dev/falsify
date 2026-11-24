# PRML negative-conformance suite (reject-vectors)

The positive suites (`spec/test-vectors/v0.1`, `v0.2`) assert that every
reference implementation produces **byte-identical** canonical output and hash
for valid manifests. This suite asserts the complementary contract: a manifest
carrying a **control / non-portable character** MUST be **rejected**, never
silently hashed.

## The rule

A PRML string field MUST NOT contain:

| Range / codepoint | What |
|---|---|
| `U+0000`–`U+001F` | C0 controls (incl. NUL, tab-adjacent) |
| `U+007F`–`U+009F` | DEL + C1 controls (incl. `U+0085` NEL, which PyYAML does not round-trip) |
| `U+2028`, `U+2029` | Line / Paragraph separators |
| `U+FEFF` | Byte-order mark (zero-width, invisible) |

These canonicalize inconsistently across YAML engines, editors, and string
contexts, so a manifest containing them could lock to a hash that does not
faithfully represent the input. Printable Unicode (emoji, CJK, accents) is
**unaffected** — it is valid in PRML string fields.

## Vectors

`reject-vectors.json` is a JSON array; each entry has `id`, `title`, `reason`,
`field` (the dotted path carrying the bad char), and `input` (the manifest).
Every `input` is otherwise valid — the **only** reason it must be rejected is the
forbidden character. Sixty-two vectors: 9 control-char (`RJ-001`..`RJ-007` carry the bad char in a *value*, `RJ-013`/`RJ-014` in a *key* — top-level and nested), 5 structural (`RJ-008`..`RJ-012`: missing required field, malformed `dataset.hash`, invalid comparator, unknown version, non-numeric threshold), 2 vacuous-bar (`RJ-015`/`RJ-016`), 2 duplicate-key (`RJ-017`/`RJ-019`) and 2 normalization (`RJ-018`/`RJ-020`). Twenty more (`RJ-021`..`RJ-040`, category `erratum-2026-11-15`, added 2026-11-15) give one input per reject rule of the PRML v0.1 erratum of 2026-11-15: YAML number spellings that are not JSON numbers (`RJ-021`..`RJ-028`), unquoted timestamps (`RJ-029`/`RJ-030`), a `!!binary` tag (`RJ-031`), non-finite numbers outside `threshold` (`RJ-032`/`RJ-033`), `seed` out of range or spelled as a float (`RJ-034`..`RJ-036`), a sequence inside a sequence (`RJ-037`), nesting past 100 levels (`RJ-038`), a lone surrogate (`RJ-039`) and content after the JSON value (`RJ-040`); their `expect` may be a list of accepted substrings. Twenty more (`RJ-041`..`RJ-060`, same category) cover the second part of that erratum: non-string YAML mapping keys (`RJ-041`..`RJ-046`), U+FFFE, U+FFFF and U+10FFFF (`RJ-047`..`RJ-049`) and fields of the wrong type (`RJ-050`..`RJ-060`). Two more (`RJ-061`, `RJ-062`, category `erratum-2026-11-25`) cover the erratum of 2026-11-25: an alias and an anchor in YAML input. Twenty-four vectors are YAML-only (`RJ-015`..`RJ-018`, `RJ-021`..`RJ-032`, `RJ-041`..`RJ-046`, `RJ-061`, `RJ-062`), so a JSON-only implementation runs 38 and skips 24 (`check_reject.py --reads json`). Each entry carries an `expect` substring its rejection message must contain, and a `category`.

## Running it

`check_reject.py` feeds each vector's `input` to an implementation's CLI (which
takes a manifest path as its last argument) and asserts a **non-zero exit**:

```sh
python3 check_reject.py -- python3 falsify_prml.py lock
python3 check_reject.py -- node impl/js/falsify.js lock
python3 check_reject.py -- impl/go/falsify-go hash
python3 check_reject.py -- impl/rust/target/release/falsify-rs hash
```

Exit 0 iff every vector was rejected. CI runs all four in
`.github/workflows/multi-lang-conformance.yml`; the Python reference is also
gated by `tests/test_reject_vectors.py` in the release test suite.

A vector that an implementation **accepts** is a parity regression: the
control-char reject rule (shipped v0.3.6) has drifted in that language. See
`spec/analysis/canonicalization-portability-v0.1.md`.
