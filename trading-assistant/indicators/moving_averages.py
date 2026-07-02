"""Simple and exponential moving averages over plain float sequences."""
from __future__ import annotations


def sma(values: list[float], period: int) -> list[float | None]:
    """Simple moving average. Returns a list the same length as `values`,
    with None for indices before enough history exists."""
    if period < 1:
        raise ValueError("period must be >= 1")
    out: list[float | None] = [None] * len(values)
    running_sum = 0.0
    for i, v in enumerate(values):
        running_sum += v
        if i >= period:
            running_sum -= values[i - period]
        if i >= period - 1:
            out[i] = running_sum / period
    return out


def ema(values: list[float], period: int) -> list[float | None]:
    """Exponential moving average, seeded with a SMA of the first `period`
    values (standard convention)."""
    if period < 1:
        raise ValueError("period must be >= 1")
    if len(values) < period:
        return [None] * len(values)

    out: list[float | None] = [None] * len(values)
    multiplier = 2.0 / (period + 1)
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = (values[i] - prev) * multiplier + prev
        out[i] = prev
    return out


def latest_ema(values: list[float], period: int) -> float | None:
    """Convenience: last non-None EMA value, or None if insufficient history."""
    series = ema(values, period)
    for v in reversed(series):
        if v is not None:
            return v
    return None
