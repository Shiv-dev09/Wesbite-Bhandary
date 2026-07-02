"""Composable pre-trade safety predicates. Each returns (passed, reason);
RiskManager runs all of them and rejects the trade if any fails."""
from __future__ import annotations

from dataclasses import dataclass

from config.schema import SafetyChecksConfig
from indicators.types import MarketContext


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    reason: str


def spread_check(context: MarketContext, config: SafetyChecksConfig) -> CheckResult:
    if context.spread_pct > config.max_spread_pct:
        return CheckResult(False, f"spread {context.spread_pct:.2f}% exceeds max {config.max_spread_pct:.2f}%")
    return CheckResult(True, "spread ok")


def volume_check(context: MarketContext, config: SafetyChecksConfig) -> CheckResult:
    if context.quote.volume < config.min_volume:
        return CheckResult(False, f"volume {context.quote.volume} below min {config.min_volume}")
    return CheckResult(True, "volume ok")


def volatility_check(context: MarketContext, config: SafetyChecksConfig) -> CheckResult:
    if context.atr_pct > config.max_atr_pct:
        return CheckResult(False, f"ATR {context.atr_pct:.2f}% exceeds max {config.max_atr_pct:.2f}% (too volatile)")
    return CheckResult(True, "volatility ok")


def circuit_limit_check(context: MarketContext, config: SafetyChecksConfig) -> CheckResult:
    ltp = context.quote.ltp
    upper = context.quote.upper_circuit
    lower = context.quote.lower_circuit
    if upper and ltp > 0:
        distance_pct = (upper - ltp) / ltp * 100.0
        if distance_pct <= config.circuit_limit_buffer_pct:
            return CheckResult(False, f"within {distance_pct:.2f}% of upper circuit")
    if lower and ltp > 0:
        distance_pct = (ltp - lower) / ltp * 100.0
        if distance_pct <= config.circuit_limit_buffer_pct:
            return CheckResult(False, f"within {distance_pct:.2f}% of lower circuit")
    return CheckResult(True, "circuit limit ok")


def margin_check(capital_required: float, available_margin: float, config: SafetyChecksConfig) -> CheckResult:
    usable = available_margin * (1 - config.min_available_margin_buffer_pct / 100.0)
    if capital_required > usable:
        return CheckResult(False, f"capital required {capital_required:.2f} exceeds usable margin {usable:.2f}")
    return CheckResult(True, "margin ok")


def run_all_market_checks(context: MarketContext, config: SafetyChecksConfig) -> list[CheckResult]:
    return [
        spread_check(context, config),
        volume_check(context, config),
        volatility_check(context, config),
        circuit_limit_check(context, config),
    ]
