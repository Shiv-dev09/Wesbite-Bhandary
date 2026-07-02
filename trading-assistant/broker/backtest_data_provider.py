"""Replays pre-loaded historical bars bar-by-bar. Fed by
backtest/data_cache.py (which reads the `bars` SQLite table, itself
populated ahead of time via a one-off get_historical_data MCP ingestion
run). No MCP access at replay time -- fully deterministic and offline."""
from __future__ import annotations

from indicators.types import Bar, Quote
from broker.market_data import MarketDataProvider


class BacktestDataProvider(MarketDataProvider):
    def __init__(self, bars_by_symbol: dict[str, list[Bar]]) -> None:
        self._bars = bars_by_symbol
        self._cursor: dict[str, int] = {symbol: 0 for symbol in bars_by_symbol}

    def set_cursor(self, symbol: str, index: int) -> None:
        self._cursor[symbol] = index

    def advance_all(self) -> bool:
        """Advances every symbol's cursor by one bar. Returns False once
        every symbol has run out of bars (end of backtest)."""
        moved = False
        for symbol, bars in self._bars.items():
            if self._cursor[symbol] + 1 < len(bars):
                self._cursor[symbol] += 1
                moved = True
        return moved

    def get_bars(self, symbol: str, lookback: int | None = None) -> list[Bar]:
        bars = self._bars.get(symbol, [])
        cursor = self._cursor.get(symbol, -1)
        window = bars[: cursor + 1]
        if lookback is not None:
            window = window[-lookback:]
        return window

    def get_quote(self, symbol: str) -> Quote | None:
        bars = self.get_bars(symbol)
        if not bars:
            return None
        last = bars[-1]
        prev_close = bars[-2].close if len(bars) > 1 else last.open
        tick = max(last.close * 0.0005, 0.05)
        return Quote(
            symbol=symbol,
            ltp=last.close,
            bid=round(last.close - tick, 2),
            ask=round(last.close + tick, 2),
            volume=last.volume,
            open=last.open,
            high=last.high,
            low=last.low,
            prev_close=prev_close,
            oi=None,
            timestamp=last.timestamp,
        )

    def is_exhausted(self, symbol: str) -> bool:
        bars = self._bars.get(symbol, [])
        return self._cursor.get(symbol, -1) >= len(bars) - 1
