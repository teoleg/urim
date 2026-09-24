"""Freeze golden expected outputs for a snapshot. One-way: refuses to overwrite.

Usage: python tools/freeze_golden.py SNAPSHOT_ID

Changing an existing expected file is a deliberate act: delete it, explain why in the
commit message, then re-run. Never do it just to make a failing test pass.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from engine.conventions.packs import get_pack
from engine.instruments.equity_option.pricer import OptionSpec, price
from engine.market.snapshot import load_snapshot

GOLDEN = Path(__file__).resolve().parent.parent / "tests" / "golden"
PACK = "EQ-EURO-US-v1"
FIELDS = ("price", "delta", "gamma", "vega", "theta", "rho", "time_to_expiry")


def main(snapshot_id: str) -> int:
    out = GOLDEN / "expected" / f"{snapshot_id}.json"
    if out.exists():
        print(f"refusing to overwrite {out}; golden values are frozen", file=sys.stderr)
        return 1
    snap = load_snapshot(GOLDEN / "snapshots" / f"{snapshot_id}.json")
    pack = get_pack(PACK)
    cases = json.loads((GOLDEN / "cases.json").read_text())["cases"]
    results = {}
    engine = None
    for c in cases:
        r = price(OptionSpec(c["option_type"], c["strike"], date.fromisoformat(c["expiry"])), snap, pack)
        results[c["id"]] = {f: getattr(r, f) for f in FIELDS}
        engine = r.engine
    doc = {
        "snapshot_id": snapshot_id,
        "pack": PACK,
        "engine": engine,
        "note": "Regression freeze produced by the engine itself; not an independent correctness proof.",
        "results": results,
    }
    out.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
