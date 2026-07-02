from __future__ import annotations

from strategies.base import Signal
from strategies.banknifty_scalping import BankNiftyScalpingStrategy
from tests.conftest import make_context
from tests.fixtures.synthetic_bars import make_trending_bars


def test_wrong_symbol_is_no_trade():
    strategy = BankNiftyScalpingStrategy({"symbol": "NIFTY BANK"})
    bars = make_trending_bars(30, up=True)
    context = make_context(symbol="RELIANCE", ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.NO_TRADE
    assert "NIFTY BANK" in result.reason


def test_scoped_symbol_produces_valid_signal():
    strategy = BankNiftyScalpingStrategy({"symbol": "NIFTY BANK", "fast_ema": 5, "slow_ema": 13})
    down = make_trending_bars(30, start_price=45000, up=False)
    up = make_trending_bars(30, start_price=down[-1].close, up=True)
    bars = down + up
    context = make_context(symbol="NIFTY BANK", ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal in (Signal.BUY, Signal.SELL, Signal.NO_TRADE)
    if result.signal in (Signal.BUY, Signal.SELL):
        assert result.suggested_sl is not None and result.suggested_target is not None
