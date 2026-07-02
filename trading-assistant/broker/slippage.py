"""Simple basis-points slippage model applied to simulated fills, so
backtest/live-paper results aren't unrealistically optimistic about fill
price versus the last-seen LTP."""
from __future__ import annotations

from strategies.base import Signal


class SlippageModel:
    def __init__(self, slippage_bps: float = 5.0) -> None:
        self.slippage_bps = slippage_bps

    def apply(self, direction: Signal, reference_price: float) -> float:
        """A BUY fills slightly worse (higher) than the reference price; a
        SELL fills slightly worse (lower)."""
        adjustment = reference_price * (self.slippage_bps / 10_000.0)
        return reference_price + adjustment if direction == Signal.BUY else reference_price - adjustment
