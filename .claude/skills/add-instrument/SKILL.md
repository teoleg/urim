---
name: add-instrument
description: Add a new financial instrument (e.g. American option, interest-rate swap, fixed-rate bond) to the Urim engine as one pluggable unit - pricer, invariants, convention pack, golden tests - and get it independently verified by Thummim. Use when asked to support, price or add a new instrument or product type.
when_to_use: Requests like add an IRS, support American options, price a bond, new instrument, extend the engine to X.
argument-hint: "[instrument-name]"
---

# Add an instrument

An instrument is **one unit**: pricer + invariants + convention pack + golden tests + an independent Thummim check. It is not done until all five exist and pass. Target instrument: `$ARGUMENTS` (ask if empty).

Follow the steps in order. Stop and ask the user at every **[ASK]**. Full checklist with file paths: [checklist.md](checklist.md).

## 1. Scope it before writing code  [ASK]

State back to the user, in one short list:
- exact product (e.g. "European call/put on a single stock, cash-settled"), and what is out of scope
- the model and why (e.g. Black-Scholes; binomial tree for American)
- market inputs it needs, and whether today's snapshot format holds them (a curve is *not* a single rate)
- outputs: price and which risk measures, with units
- the convention pack it will use (existing or new, see the `conventions` skill)
- which **invariants** can prove it wrong without a second pricer (parity, bounds, monotonicity, limits such as "American ≥ European", "swap at par rate has NPV 0")

Do not continue until the user agrees. Use plan mode for anything beyond a small variation of an existing instrument.

## 2. Market inputs

If the snapshot format lacks inputs (curves, vol surfaces), extend it in `engine/market/` with **new optional fields or a new snapshot kind**; existing snapshots and their golden values must keep loading unchanged. Use the `market-snapshot` skill for the data itself. Synthetic data only.

## 3. Convention pack

Use the `conventions` skill. New conventions mean a new versioned pack, never an edit to an existing one.

## 4. Pricer

`engine/instruments/<name>/pricer.py`, modelled on `engine/instruments/equity_option/pricer.py`:
- takes a spec, a `MarketSnapshot` and a `ConventionPack`; refuses a missing pack
- returns a result that carries `snapshot_id`, `as_of`, `synthetic_data`, full `conventions`, `engine` (library + version + method) and `units`
- refuses invalid inputs with a clear error; never silently adjusts dates or conventions

## 5. Invariants

`engine/instruments/<name>/invariants.py`, returning `CheckResult`s with severity `blocking` or `warning` (see `engine/instruments/equity_option/invariants.py`). Include at least one test that proves each blocking check **can fail** (feed it a deliberately wrong result).

## 6. Golden tests

Add cases (JSON, like `tests/golden/cases.json`) and synthetic snapshots, freeze once, then write tests. Golden values are a regression freeze, not proof of correctness; say so.

`tools/freeze_golden.py` is equity-option-specific today (one cases file, one pack). For a new instrument, generalise it (instrument name → pricer, cases file, pack) and keep its one-way rule: it must refuse to overwrite existing expected files. Frozen files under `tests/golden/expected/` are protected by a hook.

## 7. Wire it up

Add a CLI subcommand in `engine/cli.py` so the instrument is reachable as a black box. Thummim can only verify what the CLI exposes. Output must be the result JSON.

## 8. Independent verification  [ASK before delegating if the user wants to review first]

**Do not write the independent reference yourself.** Delegate to the Thummim subagent with a minimal prompt: the instrument name, the CLI command, where the snapshots and cases are. No hints about your implementation, formulas or doubts. Thummim extends `verification/` and returns PASS/FAIL. A FAIL is a finding: fix the engine or discuss with the user; never loosen Thummim's tolerances.

## 9. Done means

- full test suite green (the test-on-edit hook runs it after each edit)
- Thummim verdict PASS
- `CLAUDE.md` "Current state" and `PLAN.md` updated
- summary to the user: what was built, what the invariants prove and what they don't, any convention choices made
