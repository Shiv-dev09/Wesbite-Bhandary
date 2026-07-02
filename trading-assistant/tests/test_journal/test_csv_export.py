from __future__ import annotations

import csv

from journal.csv_export import append_closed_trade
from journal.models import Trade


def _trade(**overrides) -> Trade:
    defaults = dict(
        id=1, strategy="ema_trend_following", symbol="RELIANCE", side="BUY", entry_time="t1",
        entry_price=100.0, qty=10, trade_date="2026-06-01", exit_time="t2", exit_price=104.0,
        exit_reason="TARGET_HIT", pnl=40.0, holding_seconds=300, status="CLOSED",
    )
    defaults.update(overrides)
    return Trade(**defaults)


def test_append_creates_file_with_header(tmp_path):
    path = tmp_path / "journal.csv"
    append_closed_trade(_trade(), path)
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "RELIANCE"
    assert rows[0]["pnl"] == "40.0"


def test_append_multiple_trades_accumulates(tmp_path):
    path = tmp_path / "journal.csv"
    append_closed_trade(_trade(id=1, symbol="RELIANCE"), path)
    append_closed_trade(_trade(id=2, symbol="INFY"), path)
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 2
    assert {r["symbol"] for r in rows} == {"RELIANCE", "INFY"}


def test_append_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "journal.csv"
    append_closed_trade(_trade(), path)
    assert path.exists()
