"""CPR Breakout: trades a breakout of the prior day's Central Pivot Range,
favoring narrow-CPR days which more often trend."""
from __future__ import annotations

from indicators.cpr import central_pivot_range
from indicators.types import Bar, MarketContext
from strategies.base import Signal, StrategyBase, StrategySignal


class CprBreakoutStrategy(StrategyBase):
    name = "cpr_breakout"
    required_history_bars = 5

    def generate_signal(self, bars: list[Bar], context: MarketContext) -> StrategySignal:
        breakout_buffer_pct = float(self.params.get("breakout_buffer_pct", 0.1))
        narrow_width_pct = float(self.params.get("narrow_cpr_width_pct", 0.5))

        if not self.has_sufficient_history(bars):
            return self._no_trade("insufficient history")

        if context.prev_day_high is None or context.prev_day_low is None or context.prev_day_close is None:
            return self._no_trade("previous day OHLC unavailable")

        prev_day_bar = Bar(
            timestamp=context.now,
            open=context.prev_day_close,
            high=context.prev_day_high,
            low=context.prev_day_low,
            close=context.prev_day_close,
            volume=0,
        )
        cpr = central_pivot_range(prev_day_bar)
        last = bars[-1]

        snapshot = {"pivot": cpr.pivot, "tc": cpr.tc, "bc": cpr.bc, "cpr_width_pct": cpr.width_pct}

        breakout_up = cpr.tc * (1 + breakout_buffer_pct / 100.0)
        breakout_down = cpr.bc * (1 - breakout_buffer_pct / 100.0)
        confidence_boost = 0.1 if cpr.width_pct <= narrow_width_pct else 0.0

        if last.close > breakout_up:
            sl = cpr.pivot
            risk = last.close - sl
            target = last.close + max(risk, 0.01) * 2.0
            return StrategySignal(
                signal=Signal.BUY,
                strategy_name=self.name,
                raw_confidence=min(1.0, 0.6 + confidence_boost),
                reason=f"close {last.close:.2f} broke above CPR TC {cpr.tc:.2f}",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        if last.close < breakout_down:
            sl = cpr.pivot
            risk = sl - last.close
            target = last.close - max(risk, 0.01) * 2.0
            return StrategySignal(
                signal=Signal.SELL,
                strategy_name=self.name,
                raw_confidence=min(1.0, 0.6 + confidence_boost),
                reason=f"close {last.close:.2f} broke below CPR BC {cpr.bc:.2f}",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        return self._no_trade("price inside CPR", snapshot)
