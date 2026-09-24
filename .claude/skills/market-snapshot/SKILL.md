---
name: market-snapshot
description: Create, validate or review a market snapshot, the only market input the Urim engine accepts. Use when someone wants to price something and no suitable snapshot exists, adds or edits a file under tests/golden/snapshots/, or asks where market data comes from.
when_to_use: Requests like new snapshot, market data, price with spot X and vol Y, add a golden snapshot, is this data OK to commit.
---

# Market snapshots

The engine refuses to price without a dated, identified snapshot. A snapshot is a JSON file; nothing is ever priced from numbers typed into a prompt.

## Required fields

| Field | Meaning |
|---|---|
| `snapshot_id` | Unique ID. Synthetic: `SYN-<ASSETCLASS>-<YYYY-MM-DD>[-<VARIANT>]`, e.g. `SYN-EQ-2026-09-24-Q0`. Must equal the file name without `.json`. |
| `as_of` | ISO date the data is valid for. Pricing happens as of this date. |
| `underlying` | Name of the underlying. Synthetic data uses a made-up name (`SYNTH…`), never a real ticker. |
| `spot` | > 0 |
| `rate` | Risk-free rate, continuously compounded, flat. Decimal (0.04 = 4%). |
| `div_yield` | Continuous dividend yield, flat. Decimal. |
| `vol` | Flat Black-Scholes volatility, > 0. Decimal (0.25 = 25%). |
| `synthetic` | `true` for made-up data. `false` only for clearly public data, with the public source in `source`. |
| `source` | Where the numbers came from. For synthetic data say so in words. |

## Rules

- **Never commit licensed vendor data** (Bloomberg, Refinitiv/LSEG, ICE, exchange feeds under licence). If unsure whether data is public, make it synthetic.
- **Never edit an existing golden snapshot.** Frozen expected values depend on it. Make a new snapshot with a new ID instead.
- Percentages are decimals. If a user says "vol 25", confirm they mean 0.25 before writing it.
- Units and compounding follow the convention pack used for pricing (see the `conventions` skill). If a user's data uses another convention (e.g. annual compounding), convert explicitly and record the conversion in `source`, or ask.

## Steps

1. Copy [template.json](template.json) to `tests/golden/snapshots/<snapshot_id>.json` (or another folder for non-golden work) and fill it in.
2. Validate: `.venv/bin/python .claude/skills/market-snapshot/validate.py <path>`. It runs the engine's own loader plus the naming and labelling rules above. Fix every error it reports.
3. If the snapshot is for golden tests: freeze expected values once with `.venv/bin/python tools/freeze_golden.py <snapshot_id>`, add the ID to `SNAPSHOT_IDS` in `tests/conftest.py`, run the full test suite, then ask the Thummim subagent to verify.
