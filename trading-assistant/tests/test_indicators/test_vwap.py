from __future__ import annotations

from datetime import datetime, timedelta

from indicators.types import Bar
from indicators.vwap import session_bars_only, session_vwap, session_vwap_series
from utils.time_utils import IST


def _bar(ts, o, h, l, c, v):
    return Bar(timestamp=ts, open=o, high=h, low=l, close=c, volume=v)


def test_session_vwap_matches_manual_calc():
    ts = datetime(2026, 6, 1, 9, 15, tzinfo=IST)
    bars = [
        _bar(ts, 100, 102, 99, 101, 1000),
        _bar(ts + timedelta(minutes=1), 101, 103, 100, 102, 2000),
    ]
    typical1 = (102 + 99 + 101) / 3
    typical2 = (103 + 100 + 102) / 3
    expected = (typical1 * 1000 + typical2 * 2000) / 3000
    assert session_vwap(bars) == expected


def test_session_vwap_empty():
    assert session_vwap([]) is None


def test_session_vwap_zero_volume():
    ts = datetime(2026, 6, 1, 9, 15, tzinfo=IST)
    bars = [_bar(ts, 100, 100, 100, 100, 0)]
    assert session_vwap(bars) is None


def test_session_vwap_series_length_matches_bars():
    ts = datetime(2026, 6, 1, 9, 15, tzinfo=IST)
    bars = [_bar(ts + timedelta(minutes=i), 100, 101, 99, 100, 100) for i in range(5)]
    series = session_vwap_series(bars)
    assert len(series) == 5
    assert all(v is not None for v in series)


def test_session_bars_only_filters_to_current_day():
    day1 = datetime(2026, 6, 1, 9, 15, tzinfo=IST)
    day2 = datetime(2026, 6, 2, 9, 15, tzinfo=IST)
    bars = [_bar(day1 + timedelta(minutes=i), 100, 101, 99, 100, 100) for i in range(3)]
    bars += [_bar(day2 + timedelta(minutes=i), 100, 101, 99, 100, 100) for i in range(4)]
    result = session_bars_only(bars, day2 + timedelta(minutes=3))
    assert len(result) == 4
    assert all(b.timestamp.date() == day2.date() for b in result)
