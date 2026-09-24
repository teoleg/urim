"""Command line: python -m engine.cli price --snapshot F --type call --strike K --expiry YYYY-MM-DD --pack P"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from engine.conventions.packs import ConventionError, get_pack
from engine.instruments.equity_option.pricer import OptionSpec, price
from engine.market.snapshot import SnapshotError, load_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engine.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("price", help="price a European equity option")
    p.add_argument("--snapshot", required=True, help="path to a market snapshot JSON")
    p.add_argument("--type", required=True, choices=["call", "put"])
    p.add_argument("--strike", required=True, type=float)
    p.add_argument("--expiry", required=True, type=date.fromisoformat)
    p.add_argument("--pack", required=True, help="convention pack name, e.g. EQ-EURO-US-v1")
    args = parser.parse_args(argv)

    try:
        result = price(
            OptionSpec(args.type, args.strike, args.expiry),
            load_snapshot(args.snapshot),
            get_pack(args.pack),
        )
    except (SnapshotError, ConventionError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
