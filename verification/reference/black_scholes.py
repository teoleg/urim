"""Thummim independent reference: Black-Scholes-Merton with continuous dividend yield.

Built from first principles using only the Python standard library.
No numpy, scipy or QuantLib; no knowledge of the engine's implementation.

Conventions (taken from what the engine discloses for pack EQ-EURO-US-v1):
- day count ACT/365F: T = (expiry - as_of).days / 365
- continuous compounding, flat rate r and flat dividend yield q
- European exercise, no settlement lag (spot as of snapshot date)

Units (matching the engine's disclosed units):
- price: per 1 unit of underlying
- delta: dV/dS; gamma: d2V/dS2
- vega: dV/dsigma per 1.00 of vol (not per vol point)
- theta: dV/dt per year, where t is calendar time (= -dV/dT, T time to expiry)
- rho: dV/dr per 1.00 of rate (not per bp)
"""

from __future__ import annotations

import math
from datetime import date

SQRT_2 = math.sqrt(2.0)
INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)


def norm_cdf(x: float) -> float:
    """Standard normal CDF via erfc (accurate in both tails)."""
    return 0.5 * math.erfc(-x / SQRT_2)


def norm_pdf(x: float) -> float:
    return INV_SQRT_2PI * math.exp(-0.5 * x * x)


def year_fraction_act365f(start: date, end: date) -> float:
    """ACT/365 Fixed: actual calendar days divided by 365."""
    return (end - start).days / 365.0


def bsm(option_type: str, spot: float, strike: float, t: float,
        rate: float, div_yield: float, vol: float) -> dict:
    """Price and Greeks of a European option under BSM with continuous yield."""
    if option_type not in ("call", "put"):
        raise ValueError(f"unknown option_type {option_type!r}")
    if t <= 0.0 or vol <= 0.0:
        raise ValueError("reference requires t > 0 and vol > 0")

    s, k, r, q, sig = spot, strike, rate, div_yield, vol
    sqrt_t = math.sqrt(t)
    df_r = math.exp(-r * t)
    df_q = math.exp(-q * t)
    fwd_s = s * df_q          # S e^{-qT}
    pv_k = k * df_r           # K e^{-rT}

    d1 = (math.log(s / k) + (r - q + 0.5 * sig * sig) * t) / (sig * sqrt_t)
    d2 = d1 - sig * sqrt_t
    nd1 = norm_pdf(d1)

    gamma = df_q * nd1 / (s * sig * sqrt_t)
    vega = fwd_s * nd1 * sqrt_t
    decay = -fwd_s * nd1 * sig / (2.0 * sqrt_t)

    if option_type == "call":
        price = fwd_s * norm_cdf(d1) - pv_k * norm_cdf(d2)
        delta = df_q * norm_cdf(d1)
        theta = decay - r * pv_k * norm_cdf(d2) + q * fwd_s * norm_cdf(d1)
        rho = k * t * df_r * norm_cdf(d2)
    else:
        price = pv_k * norm_cdf(-d2) - fwd_s * norm_cdf(-d1)
        delta = -df_q * norm_cdf(-d1)
        theta = decay + r * pv_k * norm_cdf(-d2) - q * fwd_s * norm_cdf(-d1)
        rho = -k * t * df_r * norm_cdf(-d2)

    return {
        "price": price,
        "delta": delta,
        "gamma": gamma,
        "vega": vega,
        "theta": theta,
        "rho": rho,
        "time_to_expiry": t,
        "d1": d1,
        "d2": d2,
        "forward_spot_pv": fwd_s,
        "strike_pv": pv_k,
    }
