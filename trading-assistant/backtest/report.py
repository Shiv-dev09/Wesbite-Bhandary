"""Cross-strategy backtest comparison table (rich-rendered or plain text)."""
from __future__ import annotations

from backtest.engine import BacktestResult


def comparison_rows(results: list[BacktestResult]) -> list[dict]:
    rows = []
    for r in results:
        rows.append(
            {
                "strategy": r.strategy_name,
                "symbol": r.symbol,
                "trades": r.trade_count,
                "total_pnl": round(r.total_pnl, 2),
                "win_rate_pct": round(r.win_rate, 1),
                "profit_factor": round(r.profit_factor, 2) if r.profit_factor != float("inf") else "inf",
                "expectancy": round(r.expectancy, 2),
                "max_drawdown": round(r.max_drawdown, 2),
                "sharpe": round(r.sharpe_ratio, 2),
            }
        )
    return rows


def render_table(results: list[BacktestResult]):
    from rich.table import Table

    table = Table(title="Strategy Backtest Comparison")
    columns = ["strategy", "symbol", "trades", "total_pnl", "win_rate_pct", "profit_factor", "expectancy", "max_drawdown", "sharpe"]
    for col in columns:
        table.add_column(col)
    for row in comparison_rows(results):
        table.add_row(*[str(row[col]) for col in columns])
    return table
