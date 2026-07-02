from __future__ import annotations

from risk.stop_target import StopTargetCalculator
from strategies.base import Signal


def test_build_plan_enforces_minimum_risk_reward():
    calc = StopTargetCalculator(min_risk_reward=2.0, ideal_risk_reward=3.0)
    plan = calc.build_plan(Signal.BUY, entry_price=100, suggested_sl=98, suggested_target=100.5, atr=1.0)
    assert plan is not None
    assert plan.risk_reward >= 2.0
    assert plan.target > plan.entry_price


def test_build_plan_falls_back_to_atr_sl_when_missing():
    calc = StopTargetCalculator()
    plan = calc.build_plan(Signal.BUY, entry_price=100, suggested_sl=None, suggested_target=None, atr=2.0)
    assert plan is not None
    assert plan.initial_sl < plan.entry_price


def test_build_plan_returns_none_for_zero_risk():
    calc = StopTargetCalculator()
    plan = calc.build_plan(Signal.BUY, entry_price=100, suggested_sl=100, suggested_target=110, atr=1.0)
    assert plan is None


def test_trailing_stop_only_moves_in_favor_for_buy():
    calc = StopTargetCalculator()
    sl = calc.update_trailing_stop(Signal.BUY, current_price=110, current_sl=100, atr=1.0, trail_multiplier=1.0)
    assert sl >= 100
    sl_worse = calc.update_trailing_stop(Signal.BUY, current_price=90, current_sl=100, atr=1.0, trail_multiplier=1.0)
    assert sl_worse == 100  # never moves backward


def test_trailing_stop_only_moves_in_favor_for_sell():
    calc = StopTargetCalculator()
    sl = calc.update_trailing_stop(Signal.SELL, current_price=90, current_sl=100, atr=1.0, trail_multiplier=1.0)
    assert sl <= 100


def test_partial_exit_levels_sum_to_target():
    calc = StopTargetCalculator()
    levels = calc.partial_exit_levels(Signal.BUY, entry_price=100, target=110, portions=(0.5, 0.5))
    assert len(levels) == 2
    assert levels[0][0] == 105
    assert levels[-1][0] == 110


def test_partial_exit_levels_rejects_bad_portions():
    import pytest

    calc = StopTargetCalculator()
    with pytest.raises(ValueError):
        calc.partial_exit_levels(Signal.BUY, 100, 110, portions=(0.5, 0.3))
