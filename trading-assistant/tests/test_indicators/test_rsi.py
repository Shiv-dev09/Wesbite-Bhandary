from __future__ import annotations

from indicators.rsi import latest_rsi, rsi


def test_rsi_all_gains_approaches_100():
    closes = [float(i) for i in range(1, 30)]
    val = latest_rsi(closes, 14)
    assert val is not None
    assert val > 95


def test_rsi_all_losses_approaches_0():
    closes = [float(i) for i in range(30, 1, -1)]
    val = latest_rsi(closes, 14)
    assert val is not None
    assert val < 5


def test_rsi_bounded_0_100():
    closes = [100, 102, 99, 103, 101, 98, 104, 100, 97, 105, 102, 99, 101, 103, 100, 98]
    series = rsi(closes, 14)
    for v in series:
        if v is not None:
            assert 0.0 <= v <= 100.0


def test_rsi_insufficient_history():
    assert rsi([1, 2, 3], 14) == [None, None, None]
