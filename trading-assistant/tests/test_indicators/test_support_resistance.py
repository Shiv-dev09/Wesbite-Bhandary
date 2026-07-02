from __future__ import annotations

from datetime import datetime, timedelta

from indicators.support_resistance import distance_to_nearest_level_pct, nearest_levels, swing_levels
from indicators.types import Bar
from utils.time_utils import IST


def _zigzag_bars() -> list[Bar]:
    ts = datetime(2026, 6, 1, 9, 15, tzinfo=IST)
    highs_lows = [
        (101, 99), (102, 100), (108, 103), (103, 100), (101, 98),
        (100, 92), (101, 96), (103, 99), (102, 98), (101, 97),
    ]
    bars = []
    for i, (h, l) in enumerate(highs_lows):
        bars.append(Bar(timestamp=ts + timedelta(minutes=i), open=(h + l) / 2, high=h, low=l, close=(h + l) / 2, volume=1000))
    return bars


def test_swing_levels_finds_extremes():
    bars = _zigzag_bars()
    resistances, supports = swing_levels(bars, lookback=2)
    assert 108 in resistances
    assert 92 in supports


def test_nearest_levels_above_and_below_price():
    bars = _zigzag_bars()
    resistance, support = nearest_levels(price=100, bars=bars, lookback=2)
    if resistance is not None:
        assert resistance > 100
    if support is not None:
        assert support < 100


def test_distance_to_nearest_level_is_non_negative():
    bars = _zigzag_bars()
    dist = distance_to_nearest_level_pct(price=100, bars=bars, lookback=2)
    if dist is not None:
        assert dist >= 0
