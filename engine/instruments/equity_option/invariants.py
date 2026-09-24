"""Invariant checks that need no second pricer (the independent reprice is Thummim's job).

Severity follows PLAN.md §9.7: "blocking" checks must pass; "warning" checks are reported only.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from math import exp

from engine.conventions.packs import ConventionPack
from engine.instruments.equity_option.pricer import OptionSpec, PricingResult, price
from engine.market.snapshot import MarketSnapshot

BLOCKING = "blocking"
WARNING = "warning"

PARITY_TOL = 1e-9  # relative to spot
MONOTONE_TOL = 1e-12
GREEK_REL_TOL = 1e-4


@dataclass(frozen=True)
class CheckResult:
    name: str
    severity: str
    status: str  # "pass", "fail" or "n/a"
    detail: str

    @property
    def failed(self) -> bool:
        return self.status == "fail"


def _check(name: str, severity: str, ok: bool, detail: str) -> CheckResult:
    return CheckResult(name, severity, "pass" if ok else "fail", detail)


def _discounted(snap: MarketSnapshot, strike: float, t: float) -> tuple[float, float]:
    """Discounted forward spot S·e^(−qT) and discounted strike K·e^(−rT)."""
    return snap.spot * exp(-snap.div_yield * t), strike * exp(-snap.rate * t)


def check_metadata(result: PricingResult) -> CheckResult:
    missing = [k for k in ("snapshot_id", "as_of", "conventions", "engine") if not getattr(result, k)]
    return _check("metadata_present", BLOCKING, not missing, f"missing: {missing}" if missing else "ok")


def check_put_call_parity(spec, snap, pack, result) -> CheckResult:
    other = OptionSpec("put" if spec.option_type == "call" else "call", spec.strike, spec.expiry)
    other_price = price(other, snap, pack).price
    call, put = (result.price, other_price) if spec.option_type == "call" else (other_price, result.price)
    fwd, disc_k = _discounted(snap, spec.strike, result.time_to_expiry)
    err = (call - put) - (fwd - disc_k)
    return _check("put_call_parity", BLOCKING, abs(err) <= PARITY_TOL * snap.spot,
                  f"C-P={call - put:.12g}, S*e^-qT - K*e^-rT={fwd - disc_k:.12g}, error={err:.3g}")


def check_no_arbitrage_bounds(spec, snap, result) -> CheckResult:
    fwd, disc_k = _discounted(snap, spec.strike, result.time_to_expiry)
    if spec.option_type == "call":
        lower, upper = max(fwd - disc_k, 0.0), fwd
    else:
        lower, upper = max(disc_k - fwd, 0.0), disc_k
    ok = lower - MONOTONE_TOL <= result.price <= upper + MONOTONE_TOL
    return _check("no_arbitrage_bounds", BLOCKING, ok, f"{lower:.12g} <= {result.price:.12g} <= {upper:.12g}")


def check_monotone_in_vol(spec, snap, pack, result) -> CheckResult:
    lo = price(spec, replace(snap, vol=snap.vol * 0.8), pack).price
    hi = price(spec, replace(snap, vol=snap.vol * 1.2), pack).price
    ok = lo <= result.price + MONOTONE_TOL and result.price <= hi + MONOTONE_TOL
    return _check("monotone_in_vol", BLOCKING, ok, f"p(0.8v)={lo:.12g}, p(v)={result.price:.12g}, p(1.2v)={hi:.12g}")


def check_call_monotone_in_expiry(spec, snap, pack, result) -> CheckResult:
    name = "call_monotone_in_expiry"
    if spec.option_type != "call" or snap.div_yield != 0 or snap.rate < 0:
        return CheckResult(name, BLOCKING, "n/a", "applies to calls with q = 0 and r >= 0 only")
    import QuantLib as ql

    cal = pack.ql_calendar()
    later_ql = cal.advance(ql.Date(spec.expiry.day, spec.expiry.month, spec.expiry.year), ql.Period(1, ql.Months))
    later = date(later_ql.year(), later_ql.month(), later_ql.dayOfMonth())
    p_later = price(OptionSpec("call", spec.strike, later), snap, pack).price
    return _check(name, BLOCKING, result.price <= p_later + MONOTONE_TOL,
                  f"p({spec.expiry})={result.price:.12g} <= p({later})={p_later:.12g}")


def _greek_check(name: str, analytic: float, numeric: float) -> CheckResult:
    diff = abs(analytic - numeric)
    ok = diff <= GREEK_REL_TOL * max(abs(analytic), 1e-8)
    return _check(name, WARNING, ok, f"analytic={analytic:.10g}, bump={numeric:.10g}, diff={diff:.3g}")


def check_greeks_vs_bump(spec, snap, pack, result) -> list[CheckResult]:
    def p(**kw) -> float:
        return price(spec, replace(snap, **kw), pack).price

    hs = snap.spot * 1e-4
    up, down = p(spot=snap.spot + hs), p(spot=snap.spot - hs)
    hv = 1e-4
    vega = (p(vol=snap.vol + hv) - p(vol=snap.vol - hv)) / (2 * hv)
    return [
        _greek_check("delta_vs_bump", result.delta, (up - down) / (2 * hs)),
        _greek_check("gamma_vs_bump", result.gamma, (up - 2 * result.price + down) / hs**2),
        _greek_check("vega_vs_bump", result.vega, vega),
    ]


def run_checks(spec: OptionSpec, snap: MarketSnapshot, pack: ConventionPack,
               result: PricingResult | None = None) -> list[CheckResult]:
    result = result or price(spec, snap, pack)
    return [
        check_metadata(result),
        check_put_call_parity(spec, snap, pack, result),
        check_no_arbitrage_bounds(spec, snap, result),
        check_monotone_in_vol(spec, snap, pack, result),
        check_call_monotone_in_expiry(spec, snap, pack, result),
        *check_greeks_vs_bump(spec, snap, pack, result),
    ]
