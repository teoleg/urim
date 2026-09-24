# Add-instrument checklist

Tick every line before calling the instrument done.

## Scope (agreed with user)
- [ ] Product definition and out-of-scope list
- [ ] Model and reason
- [ ] Market inputs; snapshot format sufficient or extension planned
- [ ] Outputs and units
- [ ] Convention pack (existing name or new versioned pack)
- [ ] Invariants that need no second pricer

## Code
- [ ] `engine/market/…` extended with optional fields / new kind (old snapshots still load)
- [ ] `engine/conventions/packs.py` new pack (if needed) + mapping tests
- [ ] `engine/instruments/<name>/__init__.py`
- [ ] `engine/instruments/<name>/pricer.py` (refuses missing pack; result carries snapshot_id, as_of, synthetic_data, conventions, engine, units)
- [ ] `engine/instruments/<name>/invariants.py` (blocking/warning severities)
- [ ] `engine/cli.py` subcommand printing result JSON

## Tests
- [ ] Guardrail refusals (no pack, bad snapshot, invalid dates/inputs)
- [ ] Every blocking invariant has a "can fail" test
- [ ] Golden snapshots (synthetic, validated with the market-snapshot validator)
- [ ] Golden cases JSON; expected values frozen once with the freeze script
- [ ] Golden test file; full suite green

## Verification
- [ ] Thummim delegated with a minimal prompt (no implementation hints)
- [ ] Thummim verdict PASS; report read, warnings explained to the user

## Docs
- [ ] `CLAUDE.md` Current state
- [ ] `PLAN.md` (milestone / decisions if any were made)
