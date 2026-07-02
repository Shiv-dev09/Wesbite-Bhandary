from __future__ import annotations

from indicators.moving_averages import ema, latest_ema, sma


def test_sma_basic():
    values = [1, 2, 3, 4, 5]
    result = sma(values, 3)
    assert result[:2] == [None, None]
    assert result[2] == 2.0
    assert result[3] == 3.0
    assert result[4] == 4.0


def test_sma_invalid_period():
    import pytest

    with pytest.raises(ValueError):
        sma([1, 2, 3], 0)


def test_ema_seeds_with_sma_then_smooths():
    values = [1.0] * 10 + [2.0] * 10
    result = ema(values, 5)
    assert result[3] is None
    assert result[4] == 1.0
    assert result[-1] > 1.0
    assert result[-1] < 2.0


def test_ema_insufficient_history_returns_all_none():
    assert ema([1, 2], 5) == [None, None]


def test_latest_ema_trending_up():
    values = list(range(1, 30))
    val = latest_ema(values, 10)
    assert val is not None
    assert val > 15
