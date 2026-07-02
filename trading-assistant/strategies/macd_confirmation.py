"""MACD Confirmation: trades a MACD line / signal line crossover."""
from __future__ import annotations

from indicators import atr as atr_ind
from indicators import macd as macd_ind
from indicators.types import Bar, MarketContext
from strategies.base import Signal, StrategyBase, StrategySignal


class MacdConfirmationStrategy(StrategyBase):
    name = "macd_confirmation"
    required_history_bars = 35

    def generate_signal(self, bars: list[Bar], context: MarketContext) -> StrategySignal:
        fast_period = int(self.params.get("fast_period", 12))
        slow_period = int(self.params.get("slow_period", 26))
        signal_period = int(self.params.get("signal_period", 9))

        if not self.has_sufficient_history(bars):
            return self._no_trade("insufficient history")

        closes = [b.close for b in bars]
        macd_line, signal_line, _ = macd_ind.macd(closes, fast_period, slow_period, signal_period)

        current_macd, current_signal = macd_line[-1], signal_line[-1]
        prev_macd = next((v for v in reversed(macd_line[:-1]) if v is not None), None)
        prev_signal = next((v for v in reversed(signal_line[:-1]) if v is not None), None)

        if None in (current_macd, current_signal, prev_macd, prev_signal):
            return self._no_trade("MACD series not ready")

        atr_val = atr_ind.latest_atr(bars, 14) or (context.atr or 0.0)
        ltp = context.quote.ltp
        snapshot = {"macd": current_macd, "signal": current_signal}

        crossed_up = prev_macd <= prev_signal and current_macd > current_signal
        crossed_down = prev_macd >= prev_signal and current_macd < current_signal

        if crossed_up:
            sl = ltp - atr_val * 1.5
            target = ltp + atr_val * 1.5 * 2.0
            return StrategySignal(
                signal=Signal.BUY,
                strategy_name=self.name,
                raw_confidence=0.63,
                reason="MACD crossed above signal line",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        if crossed_down:
            sl = ltp + atr_val * 1.5
            target = ltp - atr_val * 1.5 * 2.0
            return StrategySignal(
                signal=Signal.SELL,
                strategy_name=self.name,
                raw_confidence=0.63,
                reason="MACD crossed below signal line",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        return self._no_trade("no MACD crossover", snapshot)
