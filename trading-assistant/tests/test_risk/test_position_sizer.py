from __future__ import annotations

from risk.position_sizer import PositionSizer


def test_basic_sizing_respects_risk_budget():
    sizer = PositionSizer()
    result = sizer.calculate(
        capital=25000, entry_price=100, sl_price=98, risk_pct=1.0, lot_size=1, available_margin=25000
    )
    # risk budget = 250, risk per unit = 2 -> raw qty 125
    assert result.quantity == 125
    assert result.is_tradable
    assert result.risk_amount == 250.0


def test_sizing_rounds_down_to_lot_size():
    sizer = PositionSizer()
    result = sizer.calculate(
        capital=25000, entry_price=100, sl_price=98, risk_pct=1.0, lot_size=50, available_margin=25000
    )
    assert result.quantity % 50 == 0
    assert result.quantity == 100  # 125 raw -> 2 lots of 50


def test_sizing_never_exceeds_available_margin():
    sizer = PositionSizer()
    result = sizer.calculate(
        capital=25000, entry_price=1000, sl_price=990, risk_pct=1.0, lot_size=1, available_margin=5000
    )
    assert result.quantity * 1000 <= 5000


def test_invalid_sl_distance_returns_zero_qty():
    sizer = PositionSizer()
    result = sizer.calculate(capital=25000, entry_price=100, sl_price=100, risk_pct=1.0, lot_size=1, available_margin=25000)
    assert not result.is_tradable


def test_margin_buffer_reduces_usable_margin():
    sizer = PositionSizer()
    result = sizer.calculate(
        capital=25000, entry_price=100, sl_price=98, risk_pct=1.0, lot_size=1,
        available_margin=250, margin_buffer_pct=50.0,
    )
    # usable margin = 125 -> max qty 1
    assert result.quantity <= 1
