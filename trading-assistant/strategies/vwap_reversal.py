"""VWAP Reversal: fades extended moves away from session VWAP once RSI
confirms an oversold/overbought extreme -- a mean-reversion setup, not a
trend-following one."""
from __future__ import annotations

from indicators import rsi as rsi_ind
from indicators.types import Bar, MarketContext
from strategies.base import Signal, StrategyBase, StrategySignal


class VwapReversalStrategy(StrategyBase):
    name = "vwap_reversal"
    required_history_bars = 20

    def generate_signal(self, bars: list[Bar], context: MarketContext) -> StrategySignal:
        deviation_pct = float(self.params.get("deviation_pct", 0.3))
        rsi_period = int(self.params.get("rsi_confirm_period", 14))
        oversold = float(self.params.get("rsi_oversold", 35))
        overbought = float(self.params.get("rsi_overbought", 65))

        if not self.has_sufficient_history(bars) or not context.session_vwap:
            return self._no_trade("insufficient history or no VWAP yet")

        closes = [b.close for b in bars]
        r = rsi_ind.latest_rsi(closes, rsi_period)
        if r is None:
            return self._no_trade("RSI not available yet")

        ltp = context.quote.ltp
        vwap = context.session_vwap
        deviation = (ltp - vwap) / vwap * 100.0

        snapshot = {"vwap": vwap, "ltp": ltp, "deviation_pct": deviation, "rsi": r}

        if deviation <= -deviation_pct and r <= oversold:
            atr_est = abs(vwap - ltp)
            sl = ltp - atr_est
            target = vwap
            return StrategySignal(
                signal=Signal.BUY,
                strategy_name=self.name,
                raw_confidence=0.65,
                reason=f"price {deviation:.2f}% below VWAP with RSI {r:.1f} oversold",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        if deviation >= deviation_pct and r >= overbought:
            atr_est = abs(ltp - vwap)
            sl = ltp + atr_est
            target = vwap
            return StrategySignal(
                signal=Signal.SELL,
                strategy_name=self.name,
                raw_confidence=0.65,
                reason=f"price {deviation:.2f}% above VWAP with RSI {r:.1f} overbought",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        return self._no_trade("no VWAP extreme with RSI confirmation", snapshot)
