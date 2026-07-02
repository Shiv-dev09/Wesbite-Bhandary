"""SQLite connection + queries for the trade journal, daily summary,
market snapshot cache, and instrument cache. This module only ever reads/
writes local SQLite state -- no MCP or broker imports here."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from journal.models import Trade

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class JournalDB:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = db_path if db_path == ":memory:" else Path(db_path)
        if isinstance(self.db_path, Path):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # -- trades -----------------------------------------------------------

    def insert_open_trade(self, trade: Trade) -> int:
        cur = self.conn.execute(
            """INSERT INTO trades
               (trade_date, strategy, symbol, side, entry_time, entry_price, qty,
                initial_sl, trailing_sl, target, indicator_snapshot, confidence_score, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')""",
            (
                trade.trade_date,
                trade.strategy,
                trade.symbol,
                trade.side,
                trade.entry_time,
                trade.entry_price,
                trade.qty,
                trade.initial_sl,
                trade.trailing_sl,
                trade.target,
                trade.indicator_snapshot_json(),
                trade.confidence_score,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_trailing_sl(self, trade_id: int, trailing_sl: float) -> None:
        self.conn.execute("UPDATE trades SET trailing_sl = ? WHERE id = ?", (trailing_sl, trade_id))
        self.conn.commit()

    def close_trade(
        self,
        trade_id: int,
        exit_time: str,
        exit_price: float,
        exit_reason: str,
        pnl: float,
        holding_seconds: int,
    ) -> None:
        self.conn.execute(
            """UPDATE trades
               SET exit_time = ?, exit_price = ?, exit_reason = ?, pnl = ?,
                   holding_seconds = ?, status = 'CLOSED'
               WHERE id = ?""",
            (exit_time, exit_price, exit_reason, pnl, holding_seconds, trade_id),
        )
        self.conn.commit()

    def get_open_trades(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM trades WHERE status = 'OPEN'").fetchall()

    def get_trades_for_date(self, trade_date: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM trades WHERE trade_date = ? ORDER BY id", (trade_date,)
        ).fetchall()

    # -- daily summary ------------------------------------------------------

    def upsert_daily_summary(
        self,
        trade_date: str,
        realized_pnl: float,
        trades_count: int,
        wins: int,
        losses: int,
        target_hit: bool,
        loss_limit_hit: bool,
    ) -> None:
        self.conn.execute(
            """INSERT INTO daily_summary (trade_date, realized_pnl, trades_count, wins, losses, target_hit, loss_limit_hit)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(trade_date) DO UPDATE SET
                 realized_pnl=excluded.realized_pnl, trades_count=excluded.trades_count,
                 wins=excluded.wins, losses=excluded.losses,
                 target_hit=excluded.target_hit, loss_limit_hit=excluded.loss_limit_hit""",
            (trade_date, realized_pnl, trades_count, wins, losses, int(target_hit), int(loss_limit_hit)),
        )
        self.conn.commit()

    # -- market snapshots (written only by utils/feed_ingest.py) ----------

    def upsert_market_snapshot(
        self,
        symbol: str,
        ts: str,
        ltp: float,
        bid: float,
        ask: float,
        volume: int,
        oi: int | None,
        ohlc_json: str,
    ) -> None:
        self.conn.execute(
            """INSERT INTO market_snapshots (symbol, ts, ltp, bid, ask, volume, oi, ohlc_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(symbol, ts) DO UPDATE SET
                 ltp=excluded.ltp, bid=excluded.bid, ask=excluded.ask,
                 volume=excluded.volume, oi=excluded.oi, ohlc_json=excluded.ohlc_json""",
            (symbol, ts, ltp, bid, ask, volume, oi, ohlc_json),
        )
        self.conn.commit()

    def latest_snapshot(self, symbol: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM market_snapshots WHERE symbol = ? ORDER BY ts DESC LIMIT 1", (symbol,)
        ).fetchone()

    # -- OHLCV bar cache (shared by backtest data_cache and live feed_ingest) --

    def upsert_bar(
        self,
        symbol: str,
        interval: str,
        ts: str,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: int,
    ) -> None:
        self.conn.execute(
            """INSERT INTO bars (symbol, interval, ts, open, high, low, close, volume)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(symbol, interval, ts) DO UPDATE SET
                 open=excluded.open, high=excluded.high, low=excluded.low,
                 close=excluded.close, volume=excluded.volume""",
            (symbol, interval, ts, open_, high, low, close, volume),
        )
        self.conn.commit()

    def get_bars(
        self, symbol: str, interval: str, from_ts: str | None = None, to_ts: str | None = None
    ) -> list[sqlite3.Row]:
        query = "SELECT * FROM bars WHERE symbol = ? AND interval = ?"
        params: list = [symbol, interval]
        if from_ts:
            query += " AND ts >= ?"
            params.append(from_ts)
        if to_ts:
            query += " AND ts <= ?"
            params.append(to_ts)
        query += " ORDER BY ts"
        return self.conn.execute(query, params).fetchall()

    # -- instrument cache (seeded via search_instruments MCP tool) --------

    def upsert_instrument(
        self,
        tradingsymbol: str,
        exchange: str,
        instrument_token: int,
        lot_size: int,
        tick_size: float,
        instrument_type: str,
        expiry: str | None,
        strike: float | None,
    ) -> None:
        self.conn.execute(
            """INSERT INTO instrument_cache
               (tradingsymbol, exchange, instrument_token, lot_size, tick_size, instrument_type, expiry, strike)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(tradingsymbol) DO UPDATE SET
                 exchange=excluded.exchange, instrument_token=excluded.instrument_token,
                 lot_size=excluded.lot_size, tick_size=excluded.tick_size,
                 instrument_type=excluded.instrument_type, expiry=excluded.expiry, strike=excluded.strike""",
            (tradingsymbol, exchange, instrument_token, lot_size, tick_size, instrument_type, expiry, strike),
        )
        self.conn.commit()

    def get_instrument(self, tradingsymbol: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM instrument_cache WHERE tradingsymbol = ?", (tradingsymbol,)
        ).fetchone()
