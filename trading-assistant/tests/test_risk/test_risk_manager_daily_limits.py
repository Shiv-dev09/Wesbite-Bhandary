from __future__ import annotations

from datetime import datetime

from risk.daily_state import DailyState
from risk.risk_manager import DAILY_STOP_MESSAGE, RiskManager
from tests.conftest import make_context
from utils.time_utils import IST


def _now(hhmm: str = "10:30") -> datetime:
    hh, mm = hhmm.split(":")
    return datetime(2026, 6, 1, int(hh), int(mm), tzinfo=IST)


def test_daily_profit_target_disables_trading(app_config):
    manager = RiskManager(app_config)
    state = DailyState(trade_date=_now().date())
    state.realized_pnl = app_config.capital.daily_profit_target
    message = manager.evaluate_daily_stop(state, _now())
    assert message == DAILY_STOP_MESSAGE
    assert state.trading_disabled
    assert state.target_hit


def test_daily_max_loss_disables_trading(app_config):
    manager = RiskManager(app_config)
    state = DailyState(trade_date=_now().date())
    state.realized_pnl = -app_config.capital.daily_max_loss
    message = manager.evaluate_daily_stop(state, _now())
    assert message == DAILY_STOP_MESSAGE
    assert state.trading_disabled
    assert state.loss_limit_hit


def test_within_limits_does_not_disable(app_config):
    manager = RiskManager(app_config)
    state = DailyState(trade_date=_now().date())
    state.realized_pnl = 100.0
    message = manager.evaluate_daily_stop(state, _now())
    assert message is None
    assert not state.trading_disabled


def test_consecutive_losses_trigger_pause(app_config):
    manager = RiskManager(app_config)
    state = DailyState(trade_date=_now().date())
    now = _now()
    for _ in range(app_config.risk_limits.consecutive_losses_trigger):
        manager.register_trade_close(state, -50.0, now)
    assert state.is_paused(now)


def test_can_enter_trade_blocked_when_disabled(app_config):
    manager = RiskManager(app_config)
    state = DailyState(trade_date=_now().date())
    state.disable("test disable")
    from strategies.base import Signal, StrategySignal

    candidate = StrategySignal(signal=Signal.BUY, strategy_name="x", raw_confidence=0.9, reason="r")
    context = make_context(ltp=100)
    decision = manager.can_enter_trade(candidate, state, context, _now(), open_positions_count=0)
    assert not decision.allowed
