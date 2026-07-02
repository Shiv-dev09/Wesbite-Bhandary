from __future__ import annotations

from datetime import datetime

import pytest

from config.loader import load_config
from config.schema import AppConfig
from indicators.types import InstrumentKind, MarketContext, Quote
from journal.db import JournalDB
from utils.time_utils import IST


@pytest.fixture
def app_config() -> AppConfig:
    return load_config()


@pytest.fixture
def memory_db() -> JournalDB:
    db = JournalDB(":memory:")
    yield db
    db.close()


def make_quote(symbol: str = "TESTSYM", ltp: float = 100.0, **overrides) -> Quote:
    defaults = dict(
        symbol=symbol,
        ltp=ltp,
        bid=ltp - 0.05,
        ask=ltp + 0.05,
        volume=100_000,
        open=ltp,
        high=ltp * 1.01,
        low=ltp * 0.99,
        prev_close=ltp,
        oi=None,
        timestamp=datetime(2026, 6, 1, 10, 0, tzinfo=IST),
    )
    defaults.update(overrides)
    return Quote(**defaults)


def make_context(symbol: str = "TESTSYM", ltp: float = 100.0, atr: float = 1.0, vwap: float | None = None, **overrides) -> MarketContext:
    quote = make_quote(symbol=symbol, ltp=ltp)
    return MarketContext(
        symbol=symbol,
        kind=overrides.pop("kind", InstrumentKind.EQUITY),
        quote=quote,
        session_vwap=vwap if vwap is not None else ltp,
        atr=atr,
        now=overrides.pop("now", datetime(2026, 6, 1, 10, 0, tzinfo=IST)),
        lot_size=overrides.pop("lot_size", 1),
        prev_day_high=overrides.pop("prev_day_high", None),
        prev_day_low=overrides.pop("prev_day_low", None),
        prev_day_close=overrides.pop("prev_day_close", None),
    )
