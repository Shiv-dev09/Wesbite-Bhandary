from __future__ import annotations

from strategies.base import Signal
from strategies.opening_range_breakout import OpeningRangeBreakoutStrategy
from tests.conftest import make_context
from tests.fixtures.synthetic_bars import make_breakout_bars


def test_breakout_above_range_triggers_buy():
    strategy = OpeningRangeBreakoutStrategy({"range_minutes": 15, "breakout_buffer_pct": 0.05})
    bars = make_breakout_bars(pre_count=15, start_price=100, breakout_pct=2.0)
    context = make_context(ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.BUY
    assert result.suggested_sl is not None
    assert result.suggested_target is not None
    assert result.suggested_target > result.suggested_sl


def test_price_inside_range_is_no_trade():
    strategy = OpeningRangeBreakoutStrategy({"range_minutes": 15})
    bars = make_breakout_bars(pre_count=15, start_price=100, breakout_pct=0.0)
    context = make_context(ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.NO_TRADE
