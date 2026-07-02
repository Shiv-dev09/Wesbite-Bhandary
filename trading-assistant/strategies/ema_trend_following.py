"""EMA Trend Following: trades in the direction of a fast/slow EMA
crossover with a minimum slope requirement to avoid chop."""
from __future__ import annotations

from indicators import atr as atr_ind
from indicators import moving_averages as ma
from indicators.types import Bar, MarketContext
from strategies.base import Signal, StrategyBase, StrategySignal


class EmaTrendFollowingStrategy(StrategyBase):
    name = "ema_trend_following"
    required_history_bars = 25

    def generate_signal(self, bars: list[Bar], context: MarketContext) -> StrategySignal:
        fast_period = int(self.params.get("fast_period", 9))
        slow_period = int(self.params.get("slow_period", 21))
        min_slope_pct = float(self.params.get("min_slope_pct", 0.02))

        if not self.has_sufficient_history(bars):
            return self._no_trade("insufficient history")

        closes = [b.close for b in bars]
        fast_series = ma.ema(closes, fast_period)
        slow_series = ma.ema(closes, slow_period)
        fast_last = fast_series[-1]
        slow_last = slow_series[-1]
        fast_prev = next((v for v in reversed(fast_series[:-1]) if v is not None), None)

        if fast_last is None or slow_last is None or fast_prev is None:
            return self._no_trade("EMA series not ready")

        slope_pct = (fast_last - fast_prev) / fast_prev * 100.0 if fast_prev else 0.0
        atr_val = atr_ind.latest_atr(bars, 14) or (context.atr or 0.0)
        ltp = context.quote.ltp

        snapshot = {"ema_fast": fast_last, "ema_slow": slow_last, "slope_pct": slope_pct}

        if fast_last > slow_last and slope_pct >= min_slope_pct:
            sl = ltp - atr_val * 1.5
            target = ltp + atr_val * 1.5 * 2.0
            return StrategySignal(
                signal=Signal.BUY,
                strategy_name=self.name,
                raw_confidence=0.6,
                reason=f"EMA{fast_period} above EMA{slow_period}, rising {slope_pct:.2f}%",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        if fast_last < slow_last and slope_pct <= -min_slope_pct:
            sl = ltp + atr_val * 1.5
            target = ltp - atr_val * 1.5 * 2.0
            return StrategySignal(
                signal=Signal.SELL,
                strategy_name=self.name,
                raw_confidence=0.6,
                reason=f"EMA{fast_period} below EMA{slow_period}, falling {slope_pct:.2f}%",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        return self._no_trade("no clear EMA trend", snapshot)
