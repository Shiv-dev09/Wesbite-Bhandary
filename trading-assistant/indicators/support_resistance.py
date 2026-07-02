"""Swing-high/swing-low based support & resistance levels."""
from __future__ import annotations

from indicators.types import Bar


def swing_levels(bars: list[Bar], lookback: int = 3) -> tuple[list[float], list[float]]:
    """Returns (resistance_levels, support_levels) found as local swing
    highs/lows within the given bar window: a bar is a swing high/low if
    it's the max/min within `lookback` bars on either side."""
    resistances: list[float] = []
    supports: list[float] = []
    n = len(bars)
    for i in range(lookback, n - lookback):
        window = bars[i - lookback : i + lookback + 1]
        if bars[i].high == max(b.high for b in window):
            resistances.append(bars[i].high)
        if bars[i].low == min(b.low for b in window):
            supports.append(bars[i].low)
    return resistances, supports


def nearest_levels(price: float, bars: list[Bar], lookback: int = 3) -> tuple[float | None, float | None]:
    """Nearest resistance above `price` and nearest support below it."""
    resistances, supports = swing_levels(bars, lookback)
    above = [r for r in resistances if r > price]
    below = [s for s in supports if s < price]
    nearest_resistance = min(above) if above else None
    nearest_support = max(below) if below else None
    return nearest_resistance, nearest_support


def distance_to_nearest_level_pct(price: float, bars: list[Bar], lookback: int = 3) -> float | None:
    """Smallest % distance from `price` to any nearby S/R level -- used by
    the confirmation engine's price-action check (closer to a level =
    higher-conviction reaction zone)."""
    resistance, support = nearest_levels(price, bars, lookback)
    distances = []
    if resistance is not None and price > 0:
        distances.append(abs(resistance - price) / price * 100.0)
    if support is not None and price > 0:
        distances.append(abs(price - support) / price * 100.0)
    return min(distances) if distances else None
