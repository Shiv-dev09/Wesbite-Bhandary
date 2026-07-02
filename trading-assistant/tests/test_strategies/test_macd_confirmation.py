from __future__ import annotations

from strategies.base import Signal
from strategies.macd_confirmation import MacdConfirmationStrategy
from tests.conftest import make_context
from tests.fixtures.synthetic_bars import make_bars, make_trending_bars


def test_downtrend_then_uptrend_produces_valid_signal():
    strategy = MacdConfirmationStrategy({"fast_period": 12, "slow_period": 26, "signal_period": 9})
    down = make_trending_bars(40, start_price=150, up=False)
    up = make_trending_bars(40, start_price=down[-1].close, up=True)
    bars = down + up
    context = make_context(ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal in (Signal.BUY, Signal.SELL, Signal.NO_TRADE)


def test_flat_market_is_no_trade():
    strategy = MacdConfirmationStrategy({})
    bars = make_bars(40, start_price=100, step=0.0, noise=0.0)
    context = make_context(ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.NO_TRADE
