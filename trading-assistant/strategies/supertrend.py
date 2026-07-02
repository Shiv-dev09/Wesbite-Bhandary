"""Supertrend: trades on a trend-direction flip of the Supertrend indicator."""
from __future__ import annotations

from indicators import supertrend as st_ind
from indicators.types import Bar, MarketContext
from strategies.base import Signal, StrategyBase, StrategySignal


class SupertrendStrategy(StrategyBase):
    name = "supertrend"
    required_history_bars = 15

    def generate_signal(self, bars: list[Bar], context: MarketContext) -> StrategySignal:
        atr_period = int(self.params.get("atr_period", 10))
        multiplier = float(self.params.get("multiplier", 3.0))

        if not self.has_sufficient_history(bars):
            return self._no_trade("insufficient history")

        series = st_ind.supertrend(bars, atr_period, multiplier)
        current = series[-1]
        previous = next((v for v in reversed(series[:-1]) if v is not None), None)

        if current is None or previous is None:
            return self._no_trade("supertrend not ready yet")

        last = bars[-1]
        snapshot = {"supertrend": current.value, "is_uptrend": float(current.is_uptrend)}

        flipped_to_uptrend = current.is_uptrend and not previous.is_uptrend
        flipped_to_downtrend = (not current.is_uptrend) and previous.is_uptrend

        if flipped_to_uptrend:
            sl = current.value
            risk = last.close - sl
            target = last.close + max(risk, 0.01) * 2.0
            return StrategySignal(
                signal=Signal.BUY,
                strategy_name=self.name,
                raw_confidence=0.68,
                reason=f"Supertrend flipped to uptrend at {current.value:.2f}",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        if flipped_to_downtrend:
            sl = current.value
            risk = sl - last.close
            target = last.close - max(risk, 0.01) * 2.0
            return StrategySignal(
                signal=Signal.SELL,
                strategy_name=self.name,
                raw_confidence=0.68,
                reason=f"Supertrend flipped to downtrend at {current.value:.2f}",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        return self._no_trade("no Supertrend flip", snapshot)
