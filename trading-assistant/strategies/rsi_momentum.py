"""RSI Momentum: trades a momentum re-entry once RSI crosses back out of an
oversold/overbought extreme, rather than trading the extreme itself."""
from __future__ import annotations

from indicators import atr as atr_ind
from indicators import rsi as rsi_ind
from indicators.types import Bar, MarketContext
from strategies.base import Signal, StrategyBase, StrategySignal


class RsiMomentumStrategy(StrategyBase):
    name = "rsi_momentum"
    required_history_bars = 20

    def generate_signal(self, bars: list[Bar], context: MarketContext) -> StrategySignal:
        period = int(self.params.get("period", 14))
        oversold = float(self.params.get("oversold", 30))
        overbought = float(self.params.get("overbought", 70))
        confirm_bars = int(self.params.get("momentum_confirm_bars", 3))

        if not self.has_sufficient_history(bars):
            return self._no_trade("insufficient history")

        closes = [b.close for b in bars]
        series = rsi_ind.rsi(closes, period)
        recent = [v for v in series[-(confirm_bars + 1) :] if v is not None]
        if len(recent) < confirm_bars + 1:
            return self._no_trade("RSI series not ready")

        current_rsi = recent[-1]
        was_extreme_recently_low = any(v <= oversold for v in recent[:-1])
        was_extreme_recently_high = any(v >= overbought for v in recent[:-1])

        atr_val = atr_ind.latest_atr(bars, 14) or (context.atr or 0.0)
        ltp = context.quote.ltp
        snapshot = {"rsi": current_rsi}

        if was_extreme_recently_low and current_rsi > oversold:
            sl = ltp - atr_val * 1.2
            target = ltp + atr_val * 1.2 * 2.0
            return StrategySignal(
                signal=Signal.BUY,
                strategy_name=self.name,
                raw_confidence=0.6,
                reason=f"RSI {current_rsi:.1f} recovering out of oversold ({oversold})",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        if was_extreme_recently_high and current_rsi < overbought:
            sl = ltp + atr_val * 1.2
            target = ltp - atr_val * 1.2 * 2.0
            return StrategySignal(
                signal=Signal.SELL,
                strategy_name=self.name,
                raw_confidence=0.6,
                reason=f"RSI {current_rsi:.1f} falling out of overbought ({overbought})",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        return self._no_trade("no RSI momentum reversal", snapshot)
