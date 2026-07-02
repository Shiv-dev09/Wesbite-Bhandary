"""Per-trading-day state: realized PnL, trade count, consecutive-loss
streak, and the daily target/loss stop flags. One instance covers exactly
one trading date; the engine creates a fresh one each session (persisted
via journal.db's daily_summary table)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class DailyState:
    trade_date: date
    realized_pnl: float = 0.0
    trades_today: int = 0
    wins: int = 0
    losses: int = 0
    consecutive_losses: int = 0
    pause_until: datetime | None = None
    target_hit: bool = False
    loss_limit_hit: bool = False
    trading_disabled: bool = False
    disabled_reason: str | None = None

    def register_closed_trade(self, pnl: float, now: datetime) -> None:
        self.realized_pnl += pnl
        self.trades_today += 1
        if pnl > 0:
            self.wins += 1
            self.consecutive_losses = 0
        else:
            self.losses += 1
            self.consecutive_losses += 1

    def win_rate(self) -> float:
        if self.trades_today == 0:
            return 0.0
        return self.wins / self.trades_today * 100.0

    def is_paused(self, now: datetime) -> bool:
        return self.pause_until is not None and now < self.pause_until

    def disable(self, reason: str) -> None:
        self.trading_disabled = True
        self.disabled_reason = reason
