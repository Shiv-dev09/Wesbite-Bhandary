from __future__ import annotations

from backtest import metrics


def test_win_rate_basic():
    assert metrics.win_rate([10, -5, 20, -1]) == 50.0


def test_win_rate_empty():
    assert metrics.win_rate([]) == 0.0


def test_profit_factor_basic():
    pf = metrics.profit_factor([100, 50, -50])
    assert pf == 3.0


def test_profit_factor_no_losses_is_inf():
    assert metrics.profit_factor([100, 50]) == float("inf")


def test_profit_factor_no_trades_is_zero():
    assert metrics.profit_factor([]) == 0.0


def test_expectancy_basic():
    assert metrics.expectancy([10, -10, 20]) == 20 / 3


def test_max_drawdown_basic():
    curve = [100, 120, 90, 110, 80, 130]
    assert metrics.max_drawdown(curve) == 40  # peak 120 -> trough 80


def test_max_drawdown_monotonic_up_is_zero():
    assert metrics.max_drawdown([100, 110, 120, 130]) == 0


def test_sharpe_ratio_needs_at_least_two_trades():
    assert metrics.sharpe_ratio([10]) == 0.0


def test_sharpe_ratio_zero_variance_is_zero():
    assert metrics.sharpe_ratio([10, 10, 10]) == 0.0


def test_sharpe_ratio_positive_for_consistent_wins():
    val = metrics.sharpe_ratio([10, 12, 8, 11, 9])
    assert val > 0
