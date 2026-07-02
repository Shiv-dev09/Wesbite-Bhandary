from __future__ import annotations

from config.schema import SafetyChecksConfig
from risk import safety_checks
from tests.conftest import make_context


def _config(**overrides) -> SafetyChecksConfig:
    defaults = dict(
        max_spread_pct=0.3, min_volume=50_000, max_atr_pct=2.5,
        circuit_limit_buffer_pct=1.0, min_available_margin_buffer_pct=10.0,
    )
    defaults.update(overrides)
    return SafetyChecksConfig(**defaults)


def test_spread_check_passes_within_limit():
    context = make_context(ltp=100)
    result = safety_checks.spread_check(context, _config())
    assert result.passed


def test_spread_check_fails_when_too_wide():
    context = make_context(ltp=100)
    context.quote = context.quote.__class__(**{**context.quote.__dict__, "bid": 90, "ask": 110})
    result = safety_checks.spread_check(context, _config(max_spread_pct=0.1))
    assert not result.passed


def test_volume_check_fails_below_min():
    context = make_context(ltp=100)
    context.quote = context.quote.__class__(**{**context.quote.__dict__, "volume": 100})
    result = safety_checks.volume_check(context, _config(min_volume=10_000))
    assert not result.passed


def test_volatility_check_fails_when_atr_too_high():
    context = make_context(ltp=100, atr=10)  # 10% of price
    result = safety_checks.volatility_check(context, _config(max_atr_pct=2.5))
    assert not result.passed


def test_circuit_limit_check_fails_near_upper_circuit():
    context = make_context(ltp=100)
    context.quote = context.quote.__class__(**{**context.quote.__dict__, "upper_circuit": 100.5})
    result = safety_checks.circuit_limit_check(context, _config(circuit_limit_buffer_pct=1.0))
    assert not result.passed


def test_margin_check_fails_when_insufficient():
    result = safety_checks.margin_check(capital_required=10_000, available_margin=10_500, config=_config(min_available_margin_buffer_pct=10.0))
    assert not result.passed


def test_margin_check_passes_with_room():
    result = safety_checks.margin_check(capital_required=1_000, available_margin=10_000, config=_config())
    assert result.passed


def test_run_all_market_checks_returns_four_results():
    context = make_context(ltp=100)
    results = safety_checks.run_all_market_checks(context, _config())
    assert len(results) == 4
