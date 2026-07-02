from __future__ import annotations

from config.schema import ConfirmationConfig
from strategies.base import Signal, StrategySignal
from strategies.confirmation import ConfirmationEngine
from tests.conftest import make_context
from tests.fixtures.synthetic_bars import make_choppy_bars, make_trending_bars


def _raw_signal(signal: Signal, confidence: float = 0.9) -> StrategySignal:
    return StrategySignal(
        signal=signal, strategy_name="test_strategy", raw_confidence=confidence, reason="synthetic raw signal"
    )


def test_non_directional_signal_passes_through_unchanged():
    engine = ConfirmationEngine(ConfirmationConfig(threshold=0.9, weights={}))
    raw = _raw_signal(Signal.NO_TRADE)
    bars = make_choppy_bars(30)
    context = make_context(ltp=bars[-1].close)
    result = engine.evaluate(raw, bars, context)
    assert result is raw


def test_strong_aligned_uptrend_can_pass_low_threshold():
    engine = ConfirmationEngine(
        ConfirmationConfig(
            threshold=0.3,
            weights={
                "trend": 0.2, "momentum": 0.2, "volume": 0.15, "price_action": 0.15,
                "vwap": 0.1, "ema": 0.1, "support_resistance": 0.1,
            },
        )
    )
    raw = _raw_signal(Signal.BUY, confidence=0.9)
    bars = make_trending_bars(60, start_price=100, up=True)
    context = make_context(ltp=bars[-1].close, vwap=bars[0].close)
    result = engine.evaluate(raw, bars, context)
    assert result.signal in (Signal.BUY, Signal.NO_TRADE)
    assert 0.0 <= result.raw_confidence <= 1.0


def test_unreasonably_high_threshold_forces_no_trade():
    engine = ConfirmationEngine(
        ConfirmationConfig(
            threshold=0.99,
            weights={
                "trend": 0.2, "momentum": 0.2, "volume": 0.15, "price_action": 0.15,
                "vwap": 0.1, "ema": 0.1, "support_resistance": 0.1,
            },
        )
    )
    raw = _raw_signal(Signal.BUY, confidence=0.5)
    bars = make_choppy_bars(60)
    context = make_context(ltp=bars[-1].close)
    result = engine.evaluate(raw, bars, context)
    assert result.signal == Signal.NO_TRADE
    assert "below threshold" in result.reason
