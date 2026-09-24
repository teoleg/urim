#!/usr/bin/env python3
"""Validate market snapshot files: engine loader rules plus Urim naming/labelling rules.

Usage: validate.py PATH [PATH ...]    Exit 0 if all valid, 1 otherwise.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from engine.market.snapshot import SnapshotError, snapshot_from_dict

SYNTHETIC_ID = re.compile(r"^SYN-[A-Z]+-\d{4}-\d{2}-\d{2}(-[A-Z0-9]+)*$")


def problems(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read JSON: {exc}"]
    try:
        snap = snapshot_from_dict(data)
    except SnapshotError as exc:
        return [str(exc)]
    out = []
    if snap.snapshot_id != path.stem:
        out.append(f"snapshot_id {snap.snapshot_id!r} does not match file name {path.stem!r}")
    if snap.synthetic:
        if not SYNTHETIC_ID.match(snap.snapshot_id):
            out.append("synthetic snapshot_id must look like SYN-<ASSETCLASS>-<YYYY-MM-DD>[-<VARIANT>]")
        elif snap.as_of.isoformat() not in snap.snapshot_id:
            out.append(f"snapshot_id date does not match as_of {snap.as_of}")
        if "synthetic" not in snap.source.lower():
            out.append("synthetic snapshot: say 'synthetic' in source")
    elif len(snap.source.strip()) < 15:
        out.append("non-synthetic snapshot: source must name the public source of every number")
    if snap.vol > 3 or abs(snap.rate) > 0.5 or abs(snap.div_yield) > 0.5:
        out.append("vol/rate/div_yield look like percentages, not decimals (0.25 = 25%)")
    return out


def main(paths: list[str]) -> int:
    if not paths:
        print(__doc__, file=sys.stderr)
        return 2
    bad = 0
    for p in map(Path, paths):
        found = problems(p)
        print(f"{'OK  ' if not found else 'FAIL'} {p}")
        for f in found:
            print(f"     - {f}")
        bad += bool(found)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
