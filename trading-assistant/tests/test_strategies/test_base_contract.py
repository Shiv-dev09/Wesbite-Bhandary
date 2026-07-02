"""Every registered strategy must honor the shared contract: return a
valid StrategySignal, respect required_history_bars, and never raise on
edge-case (too-short, flat, or noisy) bar input."""
from __future__ import annotations

import pytest

from strategies.base import Signal
from strategies.registry import STRATEGY_REGISTRY, all_strategy_names, get_strategy
from tests.conftest import make_context
from tests.fixtures.synthetic_bars import make_bars, make_choppy_bars


@pytest.mark.parametrize("name", all_strategy_names())
def test_strategy_registered_with_expected_name(name):
    cls = STRATEGY_REGISTRY[name]
    assert cls.name == name


@pytest.mark.parametrize("name", all_strategy_names())
def test_strategy_returns_no_trade_on_too_short_history(name):
    strategy = get_strategy(name, {})
    bars = make_bars(2)
    context = make_context(symbol=strategy.params.get("symbol", "TESTSYM"))
    result = strategy.generate_signal(bars, context)
    assert result.signal == Signal.NO_TRADE
    assert 0.0 <= result.raw_confidence <= 1.0


@pytest.mark.parametrize("name", all_strategy_names())
def test_strategy_never_raises_on_choppy_bars(name):
    strategy = get_strategy(name, {})
    bars = make_choppy_bars(60)
    context = make_context(symbol=strategy.params.get("symbol", "TESTSYM"), ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert result.signal in (Signal.BUY, Signal.SELL, Signal.NO_TRADE)


@pytest.mark.parametrize("name", all_strategy_names())
def test_strategy_signal_snapshot_is_dict(name):
    strategy = get_strategy(name, {})
    bars = make_choppy_bars(60)
    context = make_context(symbol=strategy.params.get("symbol", "TESTSYM"), ltp=bars[-1].close)
    result = strategy.generate_signal(bars, context)
    assert isinstance(result.indicator_snapshot, dict)
