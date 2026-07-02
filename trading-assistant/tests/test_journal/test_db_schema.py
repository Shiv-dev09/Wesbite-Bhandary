from __future__ import annotations

from journal.models import Trade


def test_insert_and_close_trade_roundtrip(memory_db):
    trade = Trade(
        strategy="ema_trend_following", symbol="RELIANCE", side="BUY", entry_time="2026-06-01T10:00:00",
        entry_price=100.0, qty=10, trade_date="2026-06-01", initial_sl=98.0, trailing_sl=98.0, target=104.0,
        indicator_snapshot={"ema_fast": 101.2}, confidence_score=0.7,
    )
    trade_id = memory_db.insert_open_trade(trade)
    assert trade_id > 0

    open_trades = memory_db.get_open_trades()
    assert len(open_trades) == 1
    assert open_trades[0]["symbol"] == "RELIANCE"
    assert Trade.indicator_snapshot_from_json(open_trades[0]["indicator_snapshot"]) == {"ema_fast": 101.2}

    memory_db.close_trade(trade_id, "2026-06-01T10:05:00", 104.0, "TARGET_HIT", 40.0, 300)
    open_trades_after = memory_db.get_open_trades()
    assert len(open_trades_after) == 0

    day_trades = memory_db.get_trades_for_date("2026-06-01")
    assert len(day_trades) == 1
    assert day_trades[0]["status"] == "CLOSED"
    assert day_trades[0]["pnl"] == 40.0


def test_update_trailing_sl(memory_db):
    trade = Trade(
        strategy="s", symbol="X", side="BUY", entry_time="t", entry_price=100.0, qty=1,
        trade_date="2026-06-01", initial_sl=98.0, trailing_sl=98.0, target=104.0,
    )
    trade_id = memory_db.insert_open_trade(trade)
    memory_db.update_trailing_sl(trade_id, 99.5)
    rows = memory_db.get_open_trades()
    assert rows[0]["trailing_sl"] == 99.5


def test_daily_summary_upsert_is_idempotent(memory_db):
    memory_db.upsert_daily_summary("2026-06-01", 500.0, 3, 2, 1, False, False)
    memory_db.upsert_daily_summary("2026-06-01", 700.0, 4, 3, 1, False, False)
    row = memory_db.conn.execute("SELECT * FROM daily_summary WHERE trade_date = ?", ("2026-06-01",)).fetchone()
    assert row["realized_pnl"] == 700.0
    assert row["trades_count"] == 4


def test_bars_upsert_and_query(memory_db):
    memory_db.upsert_bar("RELIANCE", "minute", "2026-06-01T09:15:00", 100, 101, 99, 100.5, 1000)
    memory_db.upsert_bar("RELIANCE", "minute", "2026-06-01T09:16:00", 100.5, 102, 100, 101.5, 1500)
    rows = memory_db.get_bars("RELIANCE", "minute")
    assert len(rows) == 2
    assert rows[0]["ts"] == "2026-06-01T09:15:00"


def test_market_snapshot_latest(memory_db):
    memory_db.upsert_market_snapshot("RELIANCE", "2026-06-01T09:15:00", 100.0, 99.9, 100.1, 5000, None, "{}")
    memory_db.upsert_market_snapshot("RELIANCE", "2026-06-01T09:16:00", 101.0, 100.9, 101.1, 5500, None, "{}")
    latest = memory_db.latest_snapshot("RELIANCE")
    assert latest["ltp"] == 101.0


def test_instrument_cache_roundtrip(memory_db):
    memory_db.upsert_instrument("NIFTY25JUN25000CE", "NFO", 12345, 50, 0.05, "CE", "2026-06-25", 25000.0)
    info = memory_db.get_instrument("NIFTY25JUN25000CE")
    assert info["lot_size"] == 50
    assert info["strike"] == 25000.0
