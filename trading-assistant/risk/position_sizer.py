"""Position sizing from capital, SL distance, risk %, lot size, and
available (simulated) margin. Never exceeds available margin, always
rounds down to a whole number of lots."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SizingResult:
    quantity: int
    risk_amount: float
    capital_required: float
    reason: str

    @property
    def is_tradable(self) -> bool:
        return self.quantity > 0


class PositionSizer:
    def calculate(
        self,
        capital: float,
        entry_price: float,
        sl_price: float,
        risk_pct: float,
        lot_size: int,
        available_margin: float,
        margin_buffer_pct: float = 0.0,
    ) -> SizingResult:
        if lot_size < 1:
            lot_size = 1

        risk_per_unit = abs(entry_price - sl_price)
        if risk_per_unit <= 0 or entry_price <= 0:
            return SizingResult(0, 0.0, 0.0, "invalid entry/SL price")

        risk_budget = capital * (risk_pct / 100.0)
        raw_qty = risk_budget / risk_per_unit
        lots = int(raw_qty // lot_size)
        qty = lots * lot_size

        if qty <= 0:
            return SizingResult(0, 0.0, 0.0, "risk budget too small for one lot")

        usable_margin = available_margin * (1 - margin_buffer_pct / 100.0)
        capital_required = qty * entry_price

        if capital_required > usable_margin:
            max_lots_by_margin = int((usable_margin / entry_price) // lot_size)
            qty = max_lots_by_margin * lot_size
            capital_required = qty * entry_price
            if qty <= 0:
                return SizingResult(0, 0.0, 0.0, "insufficient available margin for one lot")

        actual_risk = qty * risk_per_unit
        return SizingResult(
            quantity=qty,
            risk_amount=actual_risk,
            capital_required=capital_required,
            reason=f"{qty} qty ({qty // lot_size} lot(s)), risking {actual_risk:.2f}",
        )
