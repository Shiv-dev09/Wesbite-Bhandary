"""CLI: reads a JSON payload (from --file or stdin) already normalized from
Kite MCP get_quotes/get_ltp/get_historical_data results, and upserts it
into the local market_snapshots + bars tables that
broker/external_feed_provider.py reads from during a live-paper cycle.

This is the ONLY place market data crosses from an MCP-tool-call context
(the orchestrating Claude Code session) into this project's Python state
-- and it only ever writes read-only market data, never anything
order-related. It is invoked externally, once per poll cycle, by whatever
is driving the live-paper loop (see README.md).

Expected JSON shape:
{
  "quotes": {
    "<symbol>": {
      "ltp": float, "bid": float, "ask": float, "volume": int, "oi": int|null,
      "ohlc": {"open": float, "high": float, "low": float, "prev_close": float,
               "lower_circuit": float|null, "upper_circuit": float|null},
      "timestamp": "<ISO8601>"
    }, ...
  },
  "bars": {
    "<symbol>": [
      {"date": "<ISO8601>", "open": float, "high": float, "low": float,
       "close": float, "volume": int}, ...
    ], ...
  }
}
"""
from __future__ import annotations

import argparse
import json
import sys

from journal.db import JournalDB

DEFAULT_DB_PATH = "logs/trading_assistant.sqlite3"


def ingest_payload(db: JournalDB, payload: dict, bar_interval: str = "minute") -> tuple[int, int]:
    quotes_written = 0
    for symbol, q in payload.get("quotes", {}).items():
        ohlc = q.get("ohlc", {})
        db.upsert_market_snapshot(
            symbol=symbol,
            ts=q["timestamp"],
            ltp=q["ltp"],
            bid=q.get("bid", q["ltp"]),
            ask=q.get("ask", q["ltp"]),
            volume=q.get("volume", 0),
            oi=q.get("oi"),
            ohlc_json=json.dumps(ohlc),
        )
        quotes_written += 1

    bars_written = 0
    for symbol, candles in payload.get("bars", {}).items():
        for c in candles:
            db.upsert_bar(
                symbol,
                bar_interval,
                c["date"],
                float(c["open"]),
                float(c["high"]),
                float(c["low"]),
                float(c["close"]),
                int(c.get("volume", 0)),
            )
            bars_written += 1

    return quotes_written, bars_written


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest a normalized Kite MCP market-data snapshot into the local journal DB."
    )
    parser.add_argument("--file", type=str, default=None, help="Path to JSON payload; reads stdin if omitted")
    parser.add_argument("--db-path", type=str, default=DEFAULT_DB_PATH)
    parser.add_argument("--bar-interval", type=str, default="minute")
    args = parser.parse_args()

    raw = open(args.file, "r", encoding="utf-8").read() if args.file else sys.stdin.read()
    payload = json.loads(raw)

    db = JournalDB(args.db_path)
    try:
        quotes_written, bars_written = ingest_payload(db, payload, args.bar_interval)
    finally:
        db.close()

    print(f"Ingested {quotes_written} quote snapshot(s), {bars_written} bar(s).")


if __name__ == "__main__":
    main()
