"""Terminal dashboard: live PnL, open positions, capital remaining, today's
trades, win rate, daily target/loss progress, and current per-strategy
signals. Rendered once per poll cycle by main.py -- this module never
calls MCP or touches the broker beyond reading state it's handed."""
from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from datetime import datetime

from broker.interface import Position
from config.schema import AppConfig
from dashboard.formatters import format_currency, format_duration, format_pct
from risk.daily_state import DailyState
from strategies.base import StrategySignal


@dataclass(frozen=True)
class DashboardData:
    daily_state: DailyState
    open_positions: list[Position]
    recent_trades: list  # sqlite3.Row-like, from JournalDB.get_trades_for_date
    strategy_signals: dict[str, StrategySignal]
    available_margin: float
    now: datetime


class DashboardRenderer:
    def __init__(self, config: AppConfig, console: Console | None = None) -> None:
        self.config = config
        self.console = console or Console()

    def render(self, data: DashboardData) -> None:
        self.console.print(self.build(data))

    def build(self, data: DashboardData) -> Group:
        return Group(
            self._summary_panel(data),
            self._positions_table(data.open_positions),
            self._trades_table(data.recent_trades),
            self._signals_table(data.strategy_signals),
        )

    def _summary_panel(self, data: DashboardData) -> Panel:
        state = data.daily_state
        capital = self.config.capital
        target = capital.daily_profit_target
        max_loss = capital.daily_max_loss

        target_progress = max(0.0, min(100.0, state.realized_pnl / target * 100.0)) if target else 0.0
        loss_progress = max(0.0, min(100.0, -state.realized_pnl / max_loss * 100.0)) if max_loss else 0.0

        pnl_style = "green" if state.realized_pnl >= 0 else "red"
        lines = [
            Text.assemble(("Live PnL: ", "bold"), (format_currency(state.realized_pnl), pnl_style)),
            Text(f"Capital Remaining (available margin): {format_currency(data.available_margin)}"),
            Text(f"Today's Trades: {state.trades_today} / {self.config.risk_limits.max_trades_per_day}"),
            Text(f"Win Rate: {format_pct(state.win_rate())} ({state.wins}W / {state.losses}L)"),
            Text(f"Daily Target Progress: {format_pct(target_progress)} of {format_currency(target)}"),
            Text(f"Daily Loss-Limit Progress: {format_pct(loss_progress)} of {format_currency(max_loss)}"),
        ]
        if state.trading_disabled:
            lines.append(Text(f"TRADING STOPPED: {state.disabled_reason}", style="bold red"))
        elif state.is_paused(data.now):
            lines.append(Text(f"Paused (consecutive losses) until {state.pause_until}", style="yellow"))

        return Panel(Group(*lines), title="Daily Summary", border_style="cyan")

    def _positions_table(self, positions: list[Position]) -> Table:
        table = Table(title="Open Positions")
        for col in ["Symbol", "Side", "Qty", "Entry", "SL", "Target", "Strategy", "Entry Time"]:
            table.add_column(col)
        for p in positions:
            table.add_row(
                p.symbol, p.side.value, str(p.quantity), f"{p.entry_price:.2f}",
                f"{p.trailing_sl:.2f}", f"{p.target:.2f}", p.strategy, p.entry_time.strftime("%H:%M:%S"),
            )
        if not positions:
            table.add_row("-", "-", "-", "-", "-", "-", "-", "-")
        return table

    def _trades_table(self, trades: list) -> Table:
        table = Table(title="Today's Closed Trades")
        for col in ["Strategy", "Symbol", "Side", "Entry", "Exit", "PnL", "Reason", "Holding"]:
            table.add_column(col)
        for t in trades:
            if t["status"] != "CLOSED":
                continue
            pnl = t["pnl"] or 0.0
            pnl_text = Text(format_currency(pnl), style="green" if pnl >= 0 else "red")
            table.add_row(
                t["strategy"], t["symbol"], t["side"],
                f"{t['entry_price']:.2f}", f"{(t['exit_price'] or 0):.2f}",
                pnl_text, t["exit_reason"] or "-", format_duration(t["holding_seconds"]),
            )
        return table

    def _signals_table(self, signals: dict[str, StrategySignal]) -> Table:
        table = Table(title="Current Signals")
        for col in ["Strategy", "Signal", "Confidence", "Reason"]:
            table.add_column(col)
        for name, sig in sorted(signals.items()):
            style = {"BUY": "green", "SELL": "red", "NO_TRADE": "dim"}.get(sig.signal.value, "")
            table.add_row(name, Text(sig.signal.value, style=style), f"{sig.raw_confidence:.2f}", sig.reason)
        return table
