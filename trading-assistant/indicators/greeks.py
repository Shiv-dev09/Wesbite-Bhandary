"""Black-Scholes option pricing & greeks, computed locally since Kite does
not provide a live greeks feed. Used to filter option strikes (min delta)
for the options-based strategies."""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class OptionType(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


@dataclass(frozen=True)
class Greeks:
    delta: float
    gamma: float
    theta: float
    vega: float


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def black_scholes_greeks(
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    iv: float,
    option_type: OptionType,
    risk_free_rate: float = 0.065,
) -> Greeks:
    """Standard Black-Scholes greeks. `iv` is annualized implied volatility
    as a decimal (e.g. 0.18 for 18%). Returns zeroed greeks for degenerate
    inputs (expired/invalid) rather than raising, since callers filter on
    threshold values."""
    if spot <= 0 or strike <= 0 or time_to_expiry_years <= 0 or iv <= 0:
        return Greeks(delta=0.0, gamma=0.0, theta=0.0, vega=0.0)

    sqrt_t = math.sqrt(time_to_expiry_years)
    d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * iv * iv) * time_to_expiry_years) / (iv * sqrt_t)
    d2 = d1 - iv * sqrt_t

    pdf_d1 = _norm_pdf(d1)
    gamma = pdf_d1 / (spot * iv * sqrt_t)
    vega = spot * pdf_d1 * sqrt_t / 100.0  # per 1% IV move

    if option_type == OptionType.CALL:
        delta = _norm_cdf(d1)
        theta = (
            -(spot * pdf_d1 * iv) / (2 * sqrt_t)
            - risk_free_rate * strike * math.exp(-risk_free_rate * time_to_expiry_years) * _norm_cdf(d2)
        ) / 365.0
    else:
        delta = _norm_cdf(d1) - 1.0
        theta = (
            -(spot * pdf_d1 * iv) / (2 * sqrt_t)
            + risk_free_rate * strike * math.exp(-risk_free_rate * time_to_expiry_years) * _norm_cdf(-d2)
        ) / 365.0

    return Greeks(delta=delta, gamma=gamma, theta=theta, vega=vega)
