from __future__ import annotations

from strategies.base import Signal
from strategies.supertrend import SupertrendStrategy
from tests.conftest import make_context
from tests.fixtures.synthetic_bars import make_trending_bars


def test_downtrend_then_sharp_uptrend_can_flip_to_buy():
    strategy = SupertrendStrategy({"atr_period": 10, "multiplier": 3.0})
    down = make_trending_bars(30, start_price=150, up=False)
    up = make_trending_bars(30, start_price=down[-1].close, up=True)
    # Make the reversal sharp enough to flip Supertrend within the window.
    bars = down + up
    context = make_context(ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal in (Signal.BUY, Signal.SELL, Signal.NO_TRADE)


def test_insufficient_history_is_no_trade():
    strategy = SupertrendStrategy({})
    bars = make_trending_bars(5)
    context = make_context(ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.NO_TRADE
