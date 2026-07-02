"""Shared data types used across indicators, strategies, risk, and broker
modules. Keeping these in one place avoids every module inventing its own
bar/quote shape."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


@dataclass(frozen=True)
class Bar:
    """One OHLCV candle."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class InstrumentKind(str, Enum):
    EQUITY = "EQUITY"
    INDEX = "INDEX"
    OPTION = "OPTION"
    FUTURE = "FUTURE"


@dataclass(frozen=True)
class Quote:
    """A live (or last-known simulated) snapshot for one tradable symbol."""
    symbol: str
    ltp: float
    bid: float
    ask: float
    volume: int
    open: float
    high: float
    low: float
    prev_close: float
    oi: int | None = None
    timestamp: datetime | None = None
    lower_circuit: float | None = None
    upper_circuit: float | None = None


@dataclass
class MarketContext:
    """Everything a strategy or confirmation check needs about the current
    market state for one symbol, besides its own bar history."""
    symbol: str
    kind: InstrumentKind
    quote: Quote
    session_vwap: float
    atr: float
    now: datetime
    lot_size: int = 1
    prev_day_high: float | None = None
    prev_day_low: float | None = None
    prev_day_close: float | None = None
    extra: dict = field(default_factory=dict)

    @property
    def spread_pct(self) -> float:
        if self.quote.ltp <= 0:
            return 0.0
        return abs(self.quote.ask - self.quote.bid) / self.quote.ltp * 100.0

    @property
    def atr_pct(self) -> float:
        if self.quote.ltp <= 0:
            return 0.0
        return self.atr / self.quote.ltp * 100.0
