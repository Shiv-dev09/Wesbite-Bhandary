"""Symbol/token/lot-size/tick-size lookups, backed by the local
instrument_cache table (seeded once via a search_instruments MCP call for
the configured watchlist)."""
from __future__ import annotations

from dataclasses import dataclass

from journal.db import JournalDB


@dataclass(frozen=True)
class InstrumentInfo:
    tradingsymbol: str
    exchange: str
    instrument_token: int
    lot_size: int
    tick_size: float
    instrument_type: str
    expiry: str | None = None
    strike: float | None = None


class InstrumentRegistry:
    def __init__(self, db: JournalDB) -> None:
        self.db = db

    def upsert(self, info: InstrumentInfo) -> None:
        self.db.upsert_instrument(
            info.tradingsymbol,
            info.exchange,
            info.instrument_token,
            info.lot_size,
            info.tick_size,
            info.instrument_type,
            info.expiry,
            info.strike,
        )

    def get(self, tradingsymbol: str) -> InstrumentInfo | None:
        row = self.db.get_instrument(tradingsymbol)
        if row is None:
            return None
        return InstrumentInfo(
            tradingsymbol=row["tradingsymbol"],
            exchange=row["exchange"],
            instrument_token=row["instrument_token"],
            lot_size=row["lot_size"],
            tick_size=row["tick_size"],
            instrument_type=row["instrument_type"],
            expiry=row["expiry"],
            strike=row["strike"],
        )

    def lot_size(self, tradingsymbol: str, default: int = 1) -> int:
        info = self.get(tradingsymbol)
        return info.lot_size if info else default
