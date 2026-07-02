from __future__ import annotations

from datetime import datetime

from indicators.cpr import central_pivot_range
from indicators.types import Bar
from utils.time_utils import IST


def test_cpr_pivot_calculation():
    prev_day = Bar(
        timestamp=datetime(2026, 6, 1, 15, 30, tzinfo=IST), open=100, high=110, low=90, close=105, volume=0
    )
    cpr = central_pivot_range(prev_day)
    expected_pivot = (110 + 90 + 105) / 3.0
    assert cpr.pivot == expected_pivot
    assert cpr.bc <= cpr.pivot <= cpr.tc


def test_cpr_width_pct_and_narrow_flag():
    tight_day = Bar(timestamp=datetime(2026, 6, 1, 15, 30, tzinfo=IST), open=100, high=100.2, low=99.8, close=100, volume=0)
    cpr = central_pivot_range(tight_day)
    assert cpr.width_pct < 1.0
    assert cpr.is_narrow is True
