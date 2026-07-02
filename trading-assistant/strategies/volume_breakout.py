"""Volume Breakout: trades a price move accompanied by an unusually large
volume surge relative to recent average volume."""
from __future__ import annotations

from indicators import volume_profile as vol
from indicators.types import Bar, MarketContext
from strategies.base import Signal, StrategyBase, StrategySignal


class VolumeBreakoutStrategy(StrategyBase):
    name = "volume_breakout"
    required_history_bars = 21

    def generate_signal(self, bars: list[Bar], context: MarketContext) -> StrategySignal:
        lookback_bars = int(self.params.get("lookback_bars", 20))
        surge_multiple = float(self.params.get("volume_surge_multiple", 2.0))
        price_move_pct = float(self.params.get("price_move_pct", 0.15))

        if not self.has_sufficient_history(bars):
            return self._no_trade("insufficient history")

        rv = vol.relative_volume(bars, lookback_bars)
        last = bars[-1]
        prev = bars[-2]
        move_pct = (last.close - prev.close) / prev.close * 100.0 if prev.close else 0.0

        snapshot = {"relative_volume": rv or 0.0, "move_pct": move_pct}

        if rv is None or rv < surge_multiple:
            return self._no_trade("no volume surge", snapshot)

        atr_est = abs(last.high - last.low) or (context.atr or 0.0)

        if move_pct >= price_move_pct:
            sl = last.low
            target = last.close + (last.close - sl) * 2.0
            return StrategySignal(
                signal=Signal.BUY,
                strategy_name=self.name,
                raw_confidence=0.62,
                reason=f"volume {rv:.1f}x average with {move_pct:.2f}% up move",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        if move_pct <= -price_move_pct:
            sl = last.high
            target = last.close - (sl - last.close) * 2.0
            return StrategySignal(
                signal=Signal.SELL,
                strategy_name=self.name,
                raw_confidence=0.62,
                reason=f"volume {rv:.1f}x average with {move_pct:.2f}% down move",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        return self._no_trade("volume surge without matching price move", snapshot)
