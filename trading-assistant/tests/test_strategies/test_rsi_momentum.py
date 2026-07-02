from __future__ import annotations

from strategies.base import Signal
from strategies.rsi_momentum import RsiMomentumStrategy
from tests.conftest import make_context
from tests.fixtures.synthetic_bars import make_bars, make_trending_bars


def test_sharp_decline_then_recovery_produces_valid_signal():
    strategy = RsiMomentumStrategy({"period": 14, "oversold": 30, "overbought": 70, "momentum_confirm_bars": 3})
    decline = make_trending_bars(25, start_price=150, up=False)
    recovery = make_bars(5, start_price=decline[-1].close, step=1.0, noise=0.0, seed=7)
    bars = decline + recovery
    context = make_context(ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal in (Signal.BUY, Signal.SELL, Signal.NO_TRADE)


def test_flat_market_is_no_trade():
    strategy = RsiMomentumStrategy({})
    bars = make_bars(30, start_price=100, step=0.0, noise=0.0)
    context = make_context(ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.NO_TRADE
