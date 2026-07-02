"""Relative-volume / volume-surge detection."""
from __future__ import annotations

from indicators.types import Bar


def average_volume(bars: list[Bar], lookback: int) -> float | None:
    if len(bars) < lookback:
        return None
    window = bars[-lookback:]
    return sum(b.volume for b in window) / lookback


def relative_volume(bars: list[Bar], lookback: int = 20) -> float | None:
    """Latest bar's volume as a multiple of the average of the preceding
    `lookback` bars. >1 means above-average volume."""
    if len(bars) < lookback + 1:
        return None
    prior = bars[-(lookback + 1) : -1]
    avg = sum(b.volume for b in prior) / lookback
    if avg == 0:
        return None
    return bars[-1].volume / avg


def is_volume_surge(bars: list[Bar], lookback: int = 20, surge_multiple: float = 2.0) -> bool:
    rv = relative_volume(bars, lookback)
    return rv is not None and rv >= surge_multiple
