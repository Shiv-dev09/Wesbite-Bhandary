"""Backtest performance metrics computed from a series of closed-trade PnL
values (and an equity curve for drawdown)."""
from __future__ import annotations

import math
import statistics


def win_rate(pnls: list[float]) -> float:
    if not pnls:
        return 0.0
    wins = sum(1 for p in pnls if p > 0)
    return wins / len(pnls) * 100.0


def profit_factor(pnls: list[float]) -> float:
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def expectancy(pnls: list[float]) -> float:
    if not pnls:
        return 0.0
    return sum(pnls) / len(pnls)


def max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    worst = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        worst = max(worst, peak - value)
    return worst


def sharpe_ratio(pnls: list[float], periods_per_year: int = 252) -> float:
    """Trade-level Sharpe: mean/stdev of per-trade PnL, annualized by
    sqrt(periods_per_year). A simplified proxy suitable for comparing
    strategies within this system, not a textbook daily-return Sharpe."""
    if len(pnls) < 2:
        return 0.0
    mean = statistics.mean(pnls)
    stdev = statistics.pstdev(pnls)
    if stdev == 0:
        return 0.0
    return (mean / stdev) * math.sqrt(periods_per_year)
