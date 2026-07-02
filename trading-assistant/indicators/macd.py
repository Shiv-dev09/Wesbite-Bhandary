"""MACD (Moving Average Convergence Divergence)."""
from __future__ import annotations

from indicators.moving_averages import ema


def macd(
    closes: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Returns (macd_line, signal_line, histogram), each the same length as
    `closes`."""
    fast_ema = ema(closes, fast_period)
    slow_ema = ema(closes, slow_period)

    macd_line: list[float | None] = [None] * len(closes)
    for i in range(len(closes)):
        if fast_ema[i] is not None and slow_ema[i] is not None:
            macd_line[i] = fast_ema[i] - slow_ema[i]

    macd_values_only = [v for v in macd_line if v is not None]
    signal_start = len(closes) - len(macd_values_only)
    signal_series = ema(macd_values_only, signal_period)

    signal_line: list[float | None] = [None] * len(closes)
    for i, v in enumerate(signal_series):
        signal_line[signal_start + i] = v

    histogram: list[float | None] = [None] * len(closes)
    for i in range(len(closes)):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram[i] = macd_line[i] - signal_line[i]

    return macd_line, signal_line, histogram


def latest_macd(
    closes: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[float | None, float | None, float | None]:
    macd_line, signal_line, histogram = macd(closes, fast_period, slow_period, signal_period)
    for i in range(len(closes) - 1, -1, -1):
        if histogram[i] is not None:
            return macd_line[i], signal_line[i], histogram[i]
    return None, None, None
