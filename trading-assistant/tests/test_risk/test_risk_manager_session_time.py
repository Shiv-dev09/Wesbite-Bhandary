from __future__ import annotations

from datetime import datetime

from risk.daily_state import DailyState
from risk.risk_manager import RiskManager
from strategies.base import Signal, StrategySignal
from tests.conftest import make_context
from utils.time_utils import IST


def _dt(hh, mm):
    return datetime(2026, 6, 1, hh, mm, tzinfo=IST)


def _candidate():
    return StrategySignal(signal=Signal.BUY, strategy_name="x", raw_confidence=0.9, reason="r")


def test_before_first_trade_time_is_rejected(app_config):
    manager = RiskManager(app_config)
    state = DailyState(trade_date=_dt(9, 15).date())
    decision = manager.can_enter_trade(_candidate(), state, make_context(ltp=100), _dt(9, 16), 0)
    assert not decision.allowed
    assert "first-trade" in decision.reason


def test_after_no_new_entries_cutoff_is_rejected(app_config):
    manager = RiskManager(app_config)
    state = DailyState(trade_date=_dt(9, 15).date())
    decision = manager.can_enter_trade(_candidate(), state, make_context(ltp=100), _dt(14, 46), 0)
    assert not decision.allowed
    assert "cutoff" in decision.reason


def test_outside_session_hours_is_rejected(app_config):
    manager = RiskManager(app_config)
    state = DailyState(trade_date=_dt(9, 15).date())
    decision = manager.can_enter_trade(_candidate(), state, make_context(ltp=100), _dt(16, 0), 0)
    assert not decision.allowed


def test_normal_midday_window_is_allowed(app_config):
    manager = RiskManager(app_config)
    state = DailyState(trade_date=_dt(9, 15).date())
    decision = manager.can_enter_trade(_candidate(), state, make_context(ltp=100), _dt(11, 0), 0)
    assert decision.allowed


def test_max_open_positions_blocks_entry(app_config):
    manager = RiskManager(app_config)
    state = DailyState(trade_date=_dt(9, 15).date())
    decision = manager.can_enter_trade(
        _candidate(), state, make_context(ltp=100), _dt(11, 0),
        open_positions_count=app_config.risk_limits.max_open_positions,
    )
    assert not decision.allowed
    assert "max open positions" in decision.reason


def test_max_trades_per_day_blocks_entry(app_config):
    manager = RiskManager(app_config)
    state = DailyState(trade_date=_dt(9, 15).date())
    state.trades_today = app_config.risk_limits.max_trades_per_day
    decision = manager.can_enter_trade(_candidate(), state, make_context(ltp=100), _dt(11, 0), 0)
    assert not decision.allowed
    assert "max trades/day" in decision.reason
