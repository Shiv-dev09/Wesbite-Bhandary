"""Abstract broker contract. PaperBroker (paper_broker.py) is the sole
concrete implementation ever instantiated by this project -- see that
file's module docstring for how the paper-only guarantee is enforced."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from strategies.base import Signal


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: Signal  # BUY or SELL only
    quantity: int
    strategy: str
    initial_sl: float
    target: float
    confidence_score: float
    indicator_snapshot: dict


@dataclass(frozen=True)
class OrderResult:
    accepted: bool
    reason: str
    trade_id: int | None = None
    fill_price: float | None = None
    pnl: float | None = None


@dataclass
class Position:
    trade_id: int
    symbol: str
    side: Signal
    quantity: int
    entry_price: float
    initial_sl: float
    trailing_sl: float
    target: float
    strategy: str
    entry_time: datetime


class BrokerInterface(ABC):
    @abstractmethod
    def place_simulated_order(self, order: OrderRequest, now: datetime) -> OrderResult:
        raise NotImplementedError

    @abstractmethod
    def get_open_positions(self) -> list[Position]:
        raise NotImplementedError

    @abstractmethod
    def check_exits(self, now: datetime) -> list[OrderResult]:
        """Checks every open position's SL/trailing-SL/target against the
        latest quote and closes any that have been hit."""
        raise NotImplementedError

    @abstractmethod
    def flatten_all(self, reason: str, now: datetime) -> list[OrderResult]:
        raise NotImplementedError

    @abstractmethod
    def get_available_margin(self) -> float:
        raise NotImplementedError
