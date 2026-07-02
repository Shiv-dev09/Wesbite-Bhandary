from __future__ import annotations

from indicators.atr import atr, latest_atr, true_range_series
from indicators.supertrend import latest_supertrend, supertrend
from tests.fixtures.synthetic_bars import make_bars, make_trending_bars


def test_true_range_series_length():
    bars = make_bars(10)
    tr = true_range_series(bars)
    assert len(tr) == 10
    assert all(v >= 0 for v in tr)


def test_atr_positive_after_warmup():
    bars = make_bars(30, noise=0.3)
    val = latest_atr(bars, 14)
    assert val is not None
    assert val > 0


def test_atr_insufficient_history():
    bars = make_bars(5)
    assert atr(bars, 14) == [None] * 5


def test_supertrend_uptrend_flags_uptrend():
    bars = make_trending_bars(60, up=True)
    result = latest_supertrend(bars, period=10, multiplier=3.0)
    assert result is not None
    assert result.is_uptrend is True


def test_supertrend_downtrend_flags_downtrend():
    bars = make_trending_bars(60, up=False)
    result = latest_supertrend(bars, period=10, multiplier=3.0)
    assert result is not None
    assert result.is_uptrend is False


def test_supertrend_insufficient_history():
    bars = make_bars(5)
    series = supertrend(bars, period=10, multiplier=3.0)
    assert all(v is None for v in series)
