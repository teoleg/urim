"""Service logic shared by the REST API and the MCP server. Same guardrails for both.

Market data is referenced by snapshot ID only: callers can never pass raw numbers.
"""
from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

from engine.conventions.packs import PACKS, ConventionError, get_pack
from engine.instruments.equity_option.pricer import OptionSpec, price
from engine.market.snapshot import SnapshotError, load_snapshot

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = Path(os.environ.get("URIM_SNAPSHOT_DIR", ROOT / "tests" / "golden" / "snapshots"))
SNAPSHOT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
VERSION = "0.1.0"


class NotFound(LookupError):
    """Unknown snapshot ID."""


class BadRequest(ValueError):
    """Invalid input: missing pack, bad dates, bad option terms."""


def service_info() -> dict:
    return {
        "service": "urim",
        "version": VERSION,
        # set by Vercel on deployed builds; lets every answer be traced to a validated commit
        "commit": os.environ.get("VERCEL_GIT_COMMIT_SHA") or os.environ.get("URIM_COMMIT") or "unknown",
    }


def list_packs() -> dict:
    return {name: pack.to_dict() for name, pack in PACKS.items()}


def list_snapshots() -> list[dict]:
    out = []
    for path in sorted(SNAPSHOT_DIR.glob("*.json")):
        snap = load_snapshot(path)
        out.append({"snapshot_id": snap.snapshot_id, "as_of": snap.as_of.isoformat(),
                    "underlying": snap.underlying, "synthetic": snap.synthetic})
    return out


def _snapshot(snapshot_id: str):
    if not SNAPSHOT_ID.match(snapshot_id or ""):
        raise BadRequest(f"invalid snapshot_id {snapshot_id!r}")
    path = SNAPSHOT_DIR / f"{snapshot_id}.json"
    if not path.is_file():
        raise NotFound(f"unknown snapshot_id {snapshot_id!r}; list available ones via /snapshots or list_snapshots")
    return load_snapshot(path)


def price_european_option(snapshot_id: str, option_type: str, strike: float, expiry: str, pack: str) -> dict:
    try:
        spec = OptionSpec(option_type, float(strike), date.fromisoformat(expiry))
        result = price(spec, _snapshot(snapshot_id), get_pack(pack))
    except (ConventionError, SnapshotError, ValueError) as exc:
        if isinstance(exc, NotFound):
            raise
        raise BadRequest(str(exc)) from exc
    return {**result.to_dict(), "service": service_info()}
