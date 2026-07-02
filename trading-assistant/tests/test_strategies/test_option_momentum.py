from __future__ import annotations

from strategies.base import Signal
from strategies.option_momentum import OptionMomentumStrategy
from tests.conftest import make_context
from tests.fixtures.synthetic_bars import make_bars, make_trending_bars


def test_strong_uptrend_with_movement_triggers_call_bias():
    strategy = OptionMomentumStrategy({"underlying_ema_period": 9, "min_underlying_move_pct": 0.05})
    bars = make_trending_bars(40, start_price=100, up=True)
    context = make_context(ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.BUY


def test_dead_tape_is_no_trade_regardless_of_direction():
    strategy = OptionMomentumStrategy({"underlying_ema_period": 9, "min_underlying_move_pct": 0.01})
    bars = make_bars(40, start_price=100, step=0.001, noise=0.0)  # near-zero realized volatility
    context = make_context(ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.NO_TRADE
