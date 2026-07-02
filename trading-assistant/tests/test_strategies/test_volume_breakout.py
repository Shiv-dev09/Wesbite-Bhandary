from __future__ import annotations

from strategies.base import Signal
from strategies.volume_breakout import VolumeBreakoutStrategy
from tests.conftest import make_context
from tests.fixtures.synthetic_bars import make_bars, make_breakout_bars


def test_volume_surge_with_up_move_triggers_buy():
    strategy = VolumeBreakoutStrategy({"lookback_bars": 20, "volume_surge_multiple": 2.0, "price_move_pct": 0.1})
    bars = make_breakout_bars(pre_count=20, start_price=100, breakout_pct=2.0)
    context = make_context(ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.BUY


def test_flat_volume_is_no_trade():
    strategy = VolumeBreakoutStrategy({"lookback_bars": 20})
    bars = make_bars(25, volume=1000)
    context = make_context(ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.NO_TRADE
