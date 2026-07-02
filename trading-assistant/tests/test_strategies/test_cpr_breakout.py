from __future__ import annotations

from strategies.base import Signal
from strategies.cpr_breakout import CprBreakoutStrategy
from tests.conftest import make_context
from tests.fixtures.synthetic_bars import make_bars


def test_breakout_above_cpr_tc_triggers_buy():
    strategy = CprBreakoutStrategy({"breakout_buffer_pct": 0.05})
    bars = make_bars(10, start_price=106, step=0.5, noise=0.0)
    context = make_context(ltp=bars[-1].close, prev_day_high=110, prev_day_low=90, prev_day_close=108)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.BUY


def test_missing_prev_day_data_is_no_trade():
    strategy = CprBreakoutStrategy({})
    bars = make_bars(10, start_price=106)
    context = make_context(ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.NO_TRADE


def test_price_inside_cpr_is_no_trade():
    strategy = CprBreakoutStrategy({})
    bars = make_bars(10, start_price=101, step=0.0, noise=0.0)
    # prev_high=110, prev_low=90, prev_close=105 -> bc=100, tc=103.33, pivot=101.67
    context = make_context(ltp=101, prev_day_high=110, prev_day_low=90, prev_day_close=105)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.NO_TRADE
