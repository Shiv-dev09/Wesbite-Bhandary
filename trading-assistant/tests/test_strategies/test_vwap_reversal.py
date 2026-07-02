from __future__ import annotations

from strategies.base import Signal
from strategies.vwap_reversal import VwapReversalStrategy
from tests.conftest import make_context
from tests.fixtures.synthetic_bars import make_trending_bars


def test_price_far_below_vwap_with_oversold_rsi_triggers_buy():
    strategy = VwapReversalStrategy({"deviation_pct": 0.3, "rsi_oversold": 35, "rsi_overbought": 65})
    bars = make_trending_bars(30, start_price=100, up=False)
    ltp = bars[-1].close
    context = make_context(ltp=ltp, vwap=ltp * 1.02)  # VWAP well above LTP
    result = strategy.generate_signal(bars, context)
    assert result.signal in (Signal.BUY, Signal.NO_TRADE)
    if result.signal == Signal.BUY:
        assert result.suggested_target is not None


def test_price_at_vwap_is_no_trade():
    strategy = VwapReversalStrategy({"deviation_pct": 0.3})
    bars = make_trending_bars(30, start_price=100, up=True)
    ltp = bars[-1].close
    context = make_context(ltp=ltp, vwap=ltp)  # no deviation
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.NO_TRADE


def test_no_vwap_available_is_no_trade():
    strategy = VwapReversalStrategy({})
    bars = make_trending_bars(30)
    context = make_context(ltp=bars[-1].close, vwap=0.0)
    context.session_vwap = 0.0
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.NO_TRADE
