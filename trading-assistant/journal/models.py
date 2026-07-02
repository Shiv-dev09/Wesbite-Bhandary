"""Trade journal record."""
from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Trade:
    strategy: str
    symbol: str
    side: str  # "BUY" / "SELL"
    entry_time: str
    entry_price: float
    qty: int
    trade_date: str
    initial_sl: float | None = None
    trailing_sl: float | None = None
    target: float | None = None
    exit_time: str | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    indicator_snapshot: dict = field(default_factory=dict)
    confidence_score: float | None = None
    pnl: float | None = None
    holding_seconds: int | None = None
    status: str = "OPEN"
    id: int | None = None

    def indicator_snapshot_json(self) -> str:
        return json.dumps(self.indicator_snapshot)

    @staticmethod
    def indicator_snapshot_from_json(raw: str | None) -> dict:
        if not raw:
            return {}
        return json.loads(raw)
