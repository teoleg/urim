"""Named convention packs. The engine never picks conventions on its own."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import QuantLib as ql


class ConventionError(ValueError):
    """Raised when conventions are missing, unknown, or violated."""


@dataclass(frozen=True)
class ConventionPack:
    name: str
    day_count: str
    calendar: str
    exercise: str
    rate_compounding: str
    dividend_model: str
    vol_model: str
    settlement: str

    def to_dict(self) -> dict:
        return asdict(self)

    def ql_day_count(self) -> ql.DayCounter:
        return _DAY_COUNTS[self.day_count]

    def ql_calendar(self) -> ql.Calendar:
        return _CALENDARS[self.calendar]


_DAY_COUNTS = {"ACT/365F": ql.Actual365Fixed()}
_CALENDARS = {"NYSE": ql.UnitedStates(ql.UnitedStates.NYSE)}

PACKS: dict[str, ConventionPack] = {
    "EQ-EURO-US-v1": ConventionPack(
        name="EQ-EURO-US-v1",
        day_count="ACT/365F",
        calendar="NYSE",
        exercise="European",
        rate_compounding="continuous, flat",
        dividend_model="continuous yield, flat",
        vol_model="Black-Scholes, flat",
        settlement="none: spot taken as of snapshot date",
    ),
}


def get_pack(name: str | None) -> ConventionPack:
    if not name:
        raise ConventionError(f"no convention pack given; choose one of: {', '.join(PACKS)}")
    try:
        return PACKS[name]
    except KeyError:
        raise ConventionError(f"unknown convention pack {name!r}; known: {', '.join(PACKS)}") from None
