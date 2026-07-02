from __future__ import annotations

from indicators.macd import latest_macd, macd


def test_macd_insufficient_history_returns_none():
    macd_val, signal_val, hist_val = latest_macd([1.0] * 5)
    assert macd_val is None and signal_val is None and hist_val is None


def test_macd_uptrend_has_positive_histogram_eventually():
    closes = [100 + i * 0.5 for i in range(60)]
    macd_val, signal_val, hist_val = latest_macd(closes)
    assert macd_val is not None
    assert hist_val is not None
    assert hist_val >= 0 or macd_val > 0


def test_macd_series_length_matches_input():
    closes = [100 + i * 0.2 for i in range(50)]
    macd_line, signal_line, hist = macd(closes)
    assert len(macd_line) == len(closes)
    assert len(signal_line) == len(closes)
    assert len(hist) == len(closes)
