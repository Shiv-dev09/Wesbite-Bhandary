"""Single choke point every prospective entry passes through before
PaperBroker.place_simulated_order is called. Owns: daily target/loss stop,
session-time gating, max positions/trades, consecutive-loss pause, and
per-trade safety checks. Capital preservation over trade frequency --
returns NO_TRADE-equivalent rejections liberally rather than forcing size.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from config.schema import AppConfig
from indicators.types import MarketContext
from risk import safety_checks
from risk.daily_state import DailyState
from risk.position_sizer import SizingResult
from strategies.base import StrategySignal
from utils.time_utils import is_at_or_after, is_before, is_within

DAILY_STOP_MESSAGE = "Daily target reached. Trading stopped."


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str


class RiskManager:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def evaluate_daily_stop(self, daily_state: DailyState, now: datetime) -> str | None:
        """Called once per cycle before any new-entry evaluation. If the
        daily profit target or max loss has just been hit, flags the
        DailyState as disabled and returns the operator-facing message the
        engine should print (and act on: flatten + cancel + stop)."""
        if daily_state.trading_disabled:
            return None  # already handled this session

        if daily_state.realized_pnl >= self.config.capital.daily_profit_target:
            daily_state.target_hit = True
            daily_state.disable(f"daily profit target of {self.config.capital.daily_profit_target} reached")
            return DAILY_STOP_MESSAGE

        if daily_state.realized_pnl <= -self.config.capital.daily_max_loss:
            daily_state.loss_limit_hit = True
            daily_state.disable(f"daily max loss of {self.config.capital.daily_max_loss} hit")
            return DAILY_STOP_MESSAGE

        return None

    def register_trade_close(self, daily_state: DailyState, pnl: float, now: datetime) -> None:
        daily_state.register_closed_trade(pnl, now)
        if daily_state.consecutive_losses >= self.config.risk_limits.consecutive_losses_trigger:
            pause_minutes = self.config.risk_limits.consecutive_loss_pause_minutes
            daily_state.pause_until = now + timedelta(minutes=pause_minutes)

    def can_enter_trade(
        self,
        candidate: StrategySignal,
        daily_state: DailyState,
        context: MarketContext,
        now: datetime,
        open_positions_count: int,
        sizing: SizingResult | None = None,
    ) -> RiskDecision:
        if daily_state.trading_disabled:
            return RiskDecision(False, daily_state.disabled_reason or DAILY_STOP_MESSAGE)

        st = self.config.session_time
        if not is_within(now, st.scan_start, st.square_off_by):
            return RiskDecision(False, "outside trading session hours")
        if is_before(now, st.first_trade):
            return RiskDecision(False, f"before first-trade time {st.first_trade}")
        if is_at_or_after(now, st.no_new_entries_after):
            return RiskDecision(False, f"past no-new-entries cutoff {st.no_new_entries_after}")

        if daily_state.is_paused(now):
            return RiskDecision(False, f"paused after {self.config.risk_limits.consecutive_losses_trigger} consecutive losses until {daily_state.pause_until}")

        if daily_state.trades_today >= self.config.risk_limits.max_trades_per_day:
            return RiskDecision(False, f"max trades/day ({self.config.risk_limits.max_trades_per_day}) reached")

        if open_positions_count >= self.config.risk_limits.max_open_positions:
            return RiskDecision(False, f"max open positions ({self.config.risk_limits.max_open_positions}) reached")

        for result in safety_checks.run_all_market_checks(context, self.config.safety_checks):
            if not result.passed:
                return RiskDecision(False, result.reason)

        if sizing is not None:
            if not sizing.is_tradable:
                return RiskDecision(False, f"position sizing rejected: {sizing.reason}")

        return RiskDecision(True, "all risk checks passed")
