from __future__ import annotations

from strategies.base import Signal
from strategies.ema_trend_following import EmaTrendFollowingStrategy
from tests.conftest import make_context
from tests.fixtures.synthetic_bars import make_choppy_bars, make_trending_bars


def test_strong_uptrend_triggers_buy():
    strategy = EmaTrendFollowingStrategy({"fast_period": 9, "slow_period": 21, "min_slope_pct": 0.001})
    bars = make_trending_bars(60, start_price=100, up=True)
    context = make_context(ltp=bars[-1].close, atr=1.0)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.BUY


def test_strong_downtrend_triggers_sell():
    strategy = EmaTrendFollowingStrategy({"fast_period": 9, "slow_period": 21, "min_slope_pct": 0.001})
    bars = make_trending_bars(60, start_price=100, up=False)
    context = make_context(ltp=bars[-1].close, atr=1.0)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.SELL


def test_choppy_market_is_no_trade():
    strategy = EmaTrendFollowingStrategy({"min_slope_pct": 0.5})
    bars = make_choppy_bars(60, start_price=100)
    context = make_context(ltp=bars[-1].close, atr=1.0)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.NO_TRADE
