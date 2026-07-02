"""The only interface strategies, risk, broker, and dashboard code ever
touch for market data. Two concrete implementations exist:
BacktestDataProvider (broker/backtest_data_provider.py, replays cached
history) and ExternalFeedDataProvider (broker/external_feed_provider.py,
reads the latest snapshot written by utils/feed_ingest.py). Neither
implementation -- nor this interface -- ever imports an MCP tool."""
from __future__ import annotations

from abc import ABC, abstractmethod

from indicators.types import Bar, Quote


class MarketDataProvider(ABC):
    @abstractmethod
    def get_quote(self, symbol: str) -> Quote | None:
        """Latest quote snapshot for `symbol`, or None if unavailable."""
        raise NotImplementedError

    @abstractmethod
    def get_bars(self, symbol: str, lookback: int | None = None) -> list[Bar]:
        """OHLCV history for `symbol`, oldest first, up to the provider's
        current point in time. If `lookback` is given, returns at most the
        last `lookback` bars."""
        raise NotImplementedError
