"""Live-paper data provider. Reads the latest quote snapshot and minute
bars written by utils/feed_ingest.py into the local SQLite `bars` /
`market_snapshots` tables. Never calls Kite MCP itself -- only the
orchestrating agent (driving feed_ingest.py on a poll cadence) does that.
"""
from __future__ import annotations

import json
from datetime import datetime

from broker.market_data import MarketDataProvider
from indicators.types import Bar, Quote
from journal.db import JournalDB


class ExternalFeedDataProvider(MarketDataProvider):
    def __init__(self, db: JournalDB, bar_interval: str = "minute") -> None:
        self.db = db
        self.bar_interval = bar_interval

    def get_quote(self, symbol: str) -> Quote | None:
        row = self.db.latest_snapshot(symbol)
        if row is None:
            return None
        ohlc = json.loads(row["ohlc_json"]) if row["ohlc_json"] else {}
        return Quote(
            symbol=symbol,
            ltp=row["ltp"],
            bid=row["bid"],
            ask=row["ask"],
            volume=row["volume"] or 0,
            open=ohlc.get("open", row["ltp"]),
            high=ohlc.get("high", row["ltp"]),
            low=ohlc.get("low", row["ltp"]),
            prev_close=ohlc.get("prev_close", row["ltp"]),
            oi=row["oi"],
            timestamp=datetime.fromisoformat(row["ts"]),
            lower_circuit=ohlc.get("lower_circuit"),
            upper_circuit=ohlc.get("upper_circuit"),
        )

    def get_bars(self, symbol: str, lookback: int | None = None) -> list[Bar]:
        rows = self.db.get_bars(symbol, self.bar_interval)
        bars = [
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
        if lookback is not None:
            bars = bars[-lookback:]
        return bars
