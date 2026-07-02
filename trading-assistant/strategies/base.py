"""Shared strategy contract. Every strategy implements only generate_signal();
multi-confirmation scoring, risk gating, and sizing all live elsewhere so
strategy files stay focused on a single entry idea."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from indicators.types import Bar, MarketContext


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NO_TRADE = "NO_TRADE"


@dataclass(frozen=True)
class StrategySignal:
    signal: Signal
    strategy_name: str
    raw_confidence: float  # 0-1, this strategy's own conviction before confirmation scoring
    reason: str
    indicator_snapshot: dict[str, float] = field(default_factory=dict)
    suggested_sl: float | None = None
    suggested_target: float | None = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.raw_confidence <= 1.0):
            raise ValueError("raw_confidence must be within [0, 1]")


NO_TRADE_SIGNAL_TEMPLATE = "insufficient setup"


class StrategyBase(ABC):
    """Base class for all trading strategies.

    Subclasses must set `name` and `required_history_bars` as class
    attributes and implement `generate_signal`. Constructor takes a plain
    dict of strategy-specific params sourced from config/default.yaml
    (config.strategies.<name>.params) -- never hardcode params in the
    strategy body.
    """

    name: str = "unnamed_strategy"
    required_history_bars: int = 1

    def __init__(self, params: dict | None = None) -> None:
        self.params = params or {}

    @abstractmethod
    def generate_signal(self, bars: list[Bar], context: MarketContext) -> StrategySignal:
        """Return a StrategySignal for the latest bar. Must return
        Signal.NO_TRADE (not raise) when there isn't enough history or no
        qualifying setup exists."""
        raise NotImplementedError

    def _no_trade(self, reason: str = NO_TRADE_SIGNAL_TEMPLATE, snapshot: dict | None = None) -> StrategySignal:
        return StrategySignal(
            signal=Signal.NO_TRADE,
            strategy_name=self.name,
            raw_confidence=0.0,
            reason=reason,
            indicator_snapshot=snapshot or {},
        )

    def has_sufficient_history(self, bars: list[Bar]) -> bool:
        return len(bars) >= self.required_history_bars
