---
paths:
  - "engine/**"
  - "tools/freeze_golden.py"
---

# Engine rules (load when working on the pricing engine)

## Pricer contract
- A pricer takes a spec, a `MarketSnapshot` and a `ConventionPack`, and refuses a missing pack.
- Every result carries `snapshot_id`, `as_of`, `synthetic_data`, the full `conventions` dict, `engine` (library + version + method) and `units`. Never drop a field to simplify output.
- Refuse invalid input with a clear error. Never adjust silently: an expiry that is not a business day is refused, not rolled; an expiry on or before `as_of` is refused.

## Conventions
- Packs live in `engine/conventions/packs.py`. A pack is immutable once used: change means a new versioned pack (`EQ-EURO-US-v2`), never an edit to `v1`.
- New day counts or calendars need an explicit QuantLib mapping plus a test that the name maps to the intended object.
- Use the `conventions` skill for the full procedure.

## Instruments
- An instrument is one unit under `engine/instruments/<name>/`: pricer + invariants + convention pack + golden tests. Use the `add-instrument` skill.
- Invariants return `CheckResult`s with severity `blocking` or `warning`; every blocking check needs a test proving it can fail.
- `engine/**/validated/**` needs an accepted ADR in `docs/adr/` naming the path (the `protect_paths` hook enforces it).

## Golden values
- `tools/freeze_golden.py` is one-way and equity-option-specific. Generalise it for a new instrument; keep the refusal to overwrite.
- Golden values are a regression freeze made by the engine itself, not an independent proof of correctness.
