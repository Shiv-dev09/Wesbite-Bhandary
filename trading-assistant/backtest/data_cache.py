"""Historical bar cache: writes candles fetched via the get_historical_data
MCP tool into the shared `bars` SQLite table, and reads them back out as
Bar lists for BacktestDataProvider. No MCP access happens in this module
itself -- callers (a one-off ingestion step driven by the orchestrating
agent) pass already-fetched candle data in."""
from __future__ import annotations

from datetime import datetime

from indicators.types import Bar
from journal.db import JournalDB


def ingest_historical_candles(db: JournalDB, symbol: str, interval: str, candles: list[dict]) -> int:
    """`candles` matches Kite's get_historical_data MCP tool output shape:
    a list of dicts with date/open/high/low/close/volume keys."""
    count = 0
    for candle in candles:
        raw_date = candle["date"]
        ts = raw_date if isinstance(raw_date, str) else raw_date.isoformat()
        db.upsert_bar(
            symbol,
            interval,
            ts,
            float(candle["open"]),
            float(candle["high"]),
            float(candle["low"]),
            float(candle["close"]),
            int(candle.get("volume", 0)),
        )
        count += 1
    return count


def load_bars(
    db: JournalDB, symbols: list[str], interval: str, from_ts: str | None = None, to_ts: str | None = None
) -> dict[str, list[Bar]]:
    result: dict[str, list[Bar]] = {}
    for symbol in symbols:
        rows = db.get_bars(symbol, interval, from_ts, to_ts)
        result[symbol] = [
            Bar(
                timestamp=datetime.fromisoformat(row["ts"]),
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"] or 0,
            )
            for row in rows
        ]
    return result
