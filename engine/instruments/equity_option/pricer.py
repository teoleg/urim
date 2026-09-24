"""European equity option pricer: Black-Scholes-Merton via QuantLib."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

import QuantLib as ql

from engine.conventions.packs import ConventionError, ConventionPack
from engine.market.snapshot import MarketSnapshot

ENGINE = f"QuantLib {ql.__version__} AnalyticEuropeanEngine"
UNITS = {
    "price": "currency of the underlying, per 1 unit of underlying",
    "delta": "d price / d spot",
    "gamma": "d delta / d spot",
    "vega": "d price / d vol, per 1.00 (100 vol points)",
    "theta": "d price / d time, per year",
    "rho": "d price / d rate, per 1.00 (10000 bp)",
    "time_to_expiry": "years, per the pack's day count",
}


@dataclass(frozen=True)
class OptionSpec:
    option_type: str  # "call" or "put"
    strike: float
    expiry: date

    def __post_init__(self):
        if self.option_type not in ("call", "put"):
            raise ValueError(f"option_type must be 'call' or 'put', got {self.option_type!r}")
        if self.strike <= 0:
            raise ValueError(f"strike must be positive, got {self.strike}")


@dataclass(frozen=True)
class PricingResult:
    spec: dict
    price: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    time_to_expiry: float
    snapshot_id: str
    as_of: str
    synthetic_data: bool
    conventions: dict
    engine: str
    units: dict

    def to_dict(self) -> dict:
        return asdict(self)


def _ql_date(d: date) -> ql.Date:
    return ql.Date(d.day, d.month, d.year)


def price(spec: OptionSpec, snapshot: MarketSnapshot, pack: ConventionPack) -> PricingResult:
    if pack is None:
        raise ConventionError("a convention pack is required; conventions are never assumed")
    if pack.exercise != "European":
        raise ConventionError(f"pack {pack.name} has exercise {pack.exercise!r}; this pricer is European only")
    if spec.expiry <= snapshot.as_of:
        raise ValueError(f"expiry {spec.expiry} must be after snapshot as_of {snapshot.as_of}")

    calendar = pack.ql_calendar()
    day_count = pack.ql_day_count()
    as_of, expiry = _ql_date(snapshot.as_of), _ql_date(spec.expiry)
    if not calendar.isBusinessDay(expiry):
        raise ConventionError(
            f"expiry {spec.expiry} is not a business day in calendar {pack.calendar}; "
            "choose a business day (expiries are never auto-adjusted)"
        )

    ql.Settings.instance().evaluationDate = as_of
    spot = ql.QuoteHandle(ql.SimpleQuote(snapshot.spot))
    rate_ts = ql.YieldTermStructureHandle(ql.FlatForward(as_of, snapshot.rate, day_count, ql.Continuous))
    div_ts = ql.YieldTermStructureHandle(ql.FlatForward(as_of, snapshot.div_yield, day_count, ql.Continuous))
    vol_ts = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(as_of, calendar, snapshot.vol, day_count))
    process = ql.BlackScholesMertonProcess(spot, div_ts, rate_ts, vol_ts)

    ql_type = ql.Option.Call if spec.option_type == "call" else ql.Option.Put
    option = ql.VanillaOption(ql.PlainVanillaPayoff(ql_type, spec.strike), ql.EuropeanExercise(expiry))
    option.setPricingEngine(ql.AnalyticEuropeanEngine(process))

    return PricingResult(
        spec={"option_type": spec.option_type, "strike": spec.strike, "expiry": spec.expiry.isoformat()},
        price=option.NPV(),
        delta=option.delta(),
        gamma=option.gamma(),
        vega=option.vega(),
        theta=option.theta(),
        rho=option.rho(),
        time_to_expiry=day_count.yearFraction(as_of, expiry),
        snapshot_id=snapshot.snapshot_id,
        as_of=snapshot.as_of.isoformat(),
        synthetic_data=snapshot.synthetic,
        conventions=pack.to_dict(),
        engine=ENGINE,
        units=UNITS,
    )
