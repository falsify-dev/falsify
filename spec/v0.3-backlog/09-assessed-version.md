# v0.3 RFC issue: identifying the version that was assessed

**Status:** backlog, opened 2026-11-17. Source: our own reading of public material (listed under Background). Nobody has asked for this field. Inputs welcome.
**Tracking:** to be mirrored as an `rfc-v0.3` issue on `falsify-dev/falsify`.

## Problem

A PRML manifest fixes the bar before a run. When the thing being evaluated later changes, the bar may have to be fixed again. A reader then needs to know which version the original bar was fixed for.

v0.1 has an optional `model` mapping (§2.2): "Identifier of the model under test, if known pre-run". Test vectors use `model.id` and `model.hash`. Erratum 16 lets `model` carry other keys, such as `version`. This works when the producer controls the model and can hash it.

It works less well in two common cases:

1. **Hosted models.** The party fixing the bar uses a model through an API. It cannot hash the weights. The only identifier it has is the version string the provider publishes, and that string may be an alias that moves (for example, "latest").
2. **System and model are different things.** An AI system (a product release) is built on an underlying model. Either can change while the other stays the same. The single `model` mapping does not say which of the two an identifier refers to.

In both cases a later reader cannot tell whether a version change has happened since the bar was fixed.

## v0.1/v0.2 position

- `model` is optional and free-form beyond `id`, `hash` and `uri`.
- No field distinguishes the system from the underlying model.
- Nothing says whether an identifier is a fixed version or a moving alias.
- The amendment chain (§6) records revisions of a claim. The spec does not say whether a re-assessment after a version change is an amendment of the old claim or a new claim.

## Proposed v0.3 direction (sketch, not decided)

Option A: **guidance only.** Document a convention for existing keys, with no new key and no schema change:
- `model.version` is the provider's identifier as published.
- `model.hash` is used when available.

Option B: **an optional `subject` mapping.** It would sit alongside `model` and hold two entries:
- `system`: identifier and version of the AI system as identified by its provider.
- `model`: identifier and version of the underlying model, where known.

Each entry would carry a flag saying whether the identifier is pinned or an alias. The whole mapping is inside the hash, so it cannot be changed after the bar is fixed.

Either option also needs one sentence on re-assessment. Options:
- A new version gets a new claim, linked to the earlier one by a reference field.
- A new version gets an amendment in the same chain.

The difference matters for §6: an amendment makes the old claim non-operative, whereas a new claim leaves both standing.

## Open questions

- Should a moving alias be allowed at all, or should the verifier flag it?
- Is a reference between claims for different versions useful enough to justify a field, or is `notes` enough?
- What about the metric definition behind a `metric` URI (§2.3.1)? The URI is fixed, but the text it points to can change. Should its hash be optional too? This is a separate, weaker case and is listed here only so it is not lost.

## Background (our reading; none of these sources mentions PRML)

- **European Commission, draft FRIA template (doc 135051, November 2026).**
  - The explanatory notice gives "the version of the system or its underlying model" as an example of a change that may require the assessment to be updated.
  - The template has no field for the version that was assessed.
  - Falsify OÜ commented on this point in the public consultation (17 November 2026).
- **Payment-card and banking guidance and surveys (2026).** These discuss revalidation after a third-party model or provider changes its capabilities. They are paraphrased here, not quoted. Their licences restrict reuse.
- **Frontier Model Forum, Jailbreak Rating Framework v1.0 (November 2026).** Scores are tied to a baseline that moves over time. This is the scale-version variant of the same problem, which is also touched on in 05-sealed-disclosure ("Baseline version").
