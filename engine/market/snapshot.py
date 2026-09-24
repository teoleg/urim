"""Market snapshots: the only source of market inputs the engine accepts."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path


class SnapshotError(ValueError):
    """Raised when a snapshot is missing required identity or holds invalid data."""


@dataclass(frozen=True)
class MarketSnapshot:
    snapshot_id: str
    as_of: date
    underlying: str
    spot: float
    rate: float  # continuously compounded risk-free rate
    div_yield: float  # continuous dividend yield
    vol: float  # flat Black-Scholes volatility
    synthetic: bool
    source: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["as_of"] = self.as_of.isoformat()
        return d


_REQUIRED = ("snapshot_id", "as_of", "underlying", "spot", "rate", "div_yield", "vol", "synthetic", "source")


def snapshot_from_dict(data: dict) -> MarketSnapshot:
    missing = [k for k in _REQUIRED if data.get(k) in (None, "")]
    if missing:
        raise SnapshotError(f"snapshot missing required fields: {', '.join(missing)}")
    try:
        as_of = date.fromisoformat(str(data["as_of"]))
    except ValueError as exc:
        raise SnapshotError(f"as_of is not an ISO date: {data['as_of']!r}") from exc
    if not isinstance(data["synthetic"], bool):
        raise SnapshotError("synthetic must be true or false")
    snap = MarketSnapshot(
        snapshot_id=str(data["snapshot_id"]),
        as_of=as_of,
        underlying=str(data["underlying"]),
        spot=float(data["spot"]),
        rate=float(data["rate"]),
        div_yield=float(data["div_yield"]),
        vol=float(data["vol"]),
        synthetic=data["synthetic"],
        source=str(data["source"]),
    )
    if snap.spot <= 0:
        raise SnapshotError(f"spot must be positive, got {snap.spot}")
    if snap.vol <= 0:
        raise SnapshotError(f"vol must be positive, got {snap.vol}")
    return snap


def load_snapshot(path: str | Path) -> MarketSnapshot:
    with open(path) as f:
        return snapshot_from_dict(json.load(f))
