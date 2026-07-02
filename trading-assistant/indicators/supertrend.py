"""Supertrend indicator, built on ATR."""
from __future__ import annotations

from dataclasses import dataclass

from indicators.atr import atr
from indicators.types import Bar


@dataclass(frozen=True)
class SupertrendPoint:
    value: float
    is_uptrend: bool


def supertrend(bars: list[Bar], period: int = 10, multiplier: float = 3.0) -> list[SupertrendPoint | None]:
    n = len(bars)
    out: list[SupertrendPoint | None] = [None] * n
    if n < period + 1:
        return out

    atr_series = atr(bars, period)
    upper_band: list[float | None] = [None] * n
    lower_band: list[float | None] = [None] * n
    final_upper: list[float | None] = [None] * n
    final_lower: list[float | None] = [None] * n

    for i in range(n):
        if atr_series[i] is None:
            continue
        mid = (bars[i].high + bars[i].low) / 2.0
        upper_band[i] = mid + multiplier * atr_series[i]
        lower_band[i] = mid - multiplier * atr_series[i]

    is_uptrend = True
    for i in range(n):
        if upper_band[i] is None:
            continue

        if final_upper[i - 1] is None if i > 0 else True:
            final_upper[i] = upper_band[i]
            final_lower[i] = lower_band[i]
        else:
            final_upper[i] = (
                upper_band[i]
                if upper_band[i] < final_upper[i - 1] or bars[i - 1].close > final_upper[i - 1]
                else final_upper[i - 1]
            )
            final_lower[i] = (
                lower_band[i]
                if lower_band[i] > final_lower[i - 1] or bars[i - 1].close < final_lower[i - 1]
                else final_lower[i - 1]
            )

        close = bars[i].close
        prev_supertrend = out[i - 1] if i > 0 else None

        if prev_supertrend is None:
            is_uptrend = close >= final_lower[i]
        elif prev_supertrend.is_uptrend:
            is_uptrend = close >= final_lower[i]
        else:
            is_uptrend = close > final_upper[i]

        value = final_lower[i] if is_uptrend else final_upper[i]
        out[i] = SupertrendPoint(value=value, is_uptrend=is_uptrend)

    return out


def latest_supertrend(bars: list[Bar], period: int = 10, multiplier: float = 3.0) -> SupertrendPoint | None:
    series = supertrend(bars, period, multiplier)
    for v in reversed(series):
        if v is not None:
            return v
    return None
