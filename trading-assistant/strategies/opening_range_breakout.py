"""Opening Range Breakout (ORB): trades a breakout of the high/low set in
the first `range_minutes` of the session."""
from __future__ import annotations

from indicators.types import Bar, MarketContext
from strategies.base import Signal, StrategyBase, StrategySignal


class OpeningRangeBreakoutStrategy(StrategyBase):
    name = "opening_range_breakout"
    required_history_bars = 16  # opening range bars + at least one breakout bar

    def generate_signal(self, bars: list[Bar], context: MarketContext) -> StrategySignal:
        range_minutes = int(self.params.get("range_minutes", 15))
        breakout_buffer_pct = float(self.params.get("breakout_buffer_pct", 0.1))
        sl_buffer_pct = float(self.params.get("sl_buffer_pct", 0.1))

        if not self.has_sufficient_history(bars) or len(bars) <= range_minutes:
            return self._no_trade("not enough bars for opening range")

        opening_range = bars[:range_minutes]
        or_high = max(b.high for b in opening_range)
        or_low = min(b.low for b in opening_range)
        last = bars[-1]

        snapshot = {"or_high": or_high, "or_low": or_low, "ltp": context.quote.ltp}

        breakout_up = or_high * (1 + breakout_buffer_pct / 100.0)
        breakout_down = or_low * (1 - breakout_buffer_pct / 100.0)

        if last.close > breakout_up:
            sl = or_low * (1 - sl_buffer_pct / 100.0)
            risk = last.close - sl
            target = last.close + risk * 2.0
            return StrategySignal(
                signal=Signal.BUY,
                strategy_name=self.name,
                raw_confidence=0.7,
                reason=f"close {last.close:.2f} broke above opening range high {or_high:.2f}",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        if last.close < breakout_down:
            sl = or_high * (1 + sl_buffer_pct / 100.0)
            risk = sl - last.close
            target = last.close - risk * 2.0
            return StrategySignal(
                signal=Signal.SELL,
                strategy_name=self.name,
                raw_confidence=0.7,
                reason=f"close {last.close:.2f} broke below opening range low {or_low:.2f}",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        return self._no_trade("price within opening range", snapshot)
