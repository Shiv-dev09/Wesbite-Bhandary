"""Mirrors closed trades to a CSV file for spreadsheet-friendly review,
alongside the SQLite journal (which remains the source of truth)."""
from __future__ import annotations

import csv
from pathlib import Path

from journal.models import Trade

CSV_FIELDS = [
    "id", "trade_date", "strategy", "symbol", "side", "entry_time", "entry_price",
    "exit_time", "exit_price", "qty", "initial_sl", "trailing_sl", "target",
    "exit_reason", "confidence_score", "pnl", "holding_seconds", "status",
]


def append_closed_trade(trade: Trade, csv_path: str | Path) -> None:
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow({field: getattr(trade, field) for field in CSV_FIELDS})
