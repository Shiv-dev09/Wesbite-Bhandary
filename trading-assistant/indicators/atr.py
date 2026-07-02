"""Average True Range (Wilder's smoothing)."""
from __future__ import annotations

from indicators.types import Bar


def true_range_series(bars: list[Bar]) -> list[float]:
    out: list[float] = []
    for i, bar in enumerate(bars):
        if i == 0:
            out.append(bar.high - bar.low)
            continue
        prev_close = bars[i - 1].close
        tr = max(
            bar.high - bar.low,
            abs(bar.high - prev_close),
            abs(bar.low - prev_close),
        )
        out.append(tr)
    return out


def atr(bars: list[Bar], period: int = 14) -> list[float | None]:
    n = len(bars)
    out: list[float | None] = [None] * n
    if n < period:
        return out

    tr = true_range_series(bars)
    avg = sum(tr[:period]) / period
    out[period - 1] = avg
    for i in range(period, n):
        avg = (avg * (period - 1) + tr[i]) / period
        out[i] = avg
    return out


def latest_atr(bars: list[Bar], period: int = 14) -> float | None:
    series = atr(bars, period)
    for v in reversed(series):
        if v is not None:
            return v
    return None
