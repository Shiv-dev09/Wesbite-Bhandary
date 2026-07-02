"""BankNifty Scalping: a fast dual-EMA crossover scalp with fixed
point-based (not percentage-based) SL/target, intended for short-holding-
period trades on BANKNIFTY's larger point moves."""
from __future__ import annotations

from indicators import moving_averages as ma
from indicators.types import Bar, MarketContext
from strategies.base import Signal, StrategyBase, StrategySignal


class BankNiftyScalpingStrategy(StrategyBase):
    name = "banknifty_scalping"
    required_history_bars = 15

    def generate_signal(self, bars: list[Bar], context: MarketContext) -> StrategySignal:
        target_symbol = self.params.get("symbol", "NIFTY BANK")
        if context.symbol != target_symbol:
            return self._no_trade(f"strategy scoped to {target_symbol}, got {context.symbol}")

        fast_period = int(self.params.get("fast_ema", 5))
        slow_period = int(self.params.get("slow_ema", 13))
        target_points = float(self.params.get("target_points", 40))
        sl_points = float(self.params.get("sl_points", 20))

        if not self.has_sufficient_history(bars):
            return self._no_trade("insufficient history")

        closes = [b.close for b in bars]
        fast_series = ma.ema(closes, fast_period)
        slow_series = ma.ema(closes, slow_period)
        fast_last, slow_last = fast_series[-1], slow_series[-1]
        fast_prev = next((v for v in reversed(fast_series[:-1]) if v is not None), None)
        slow_prev = next((v for v in reversed(slow_series[:-1]) if v is not None), None)

        if None in (fast_last, slow_last, fast_prev, slow_prev):
            return self._no_trade("EMA series not ready")

        ltp = context.quote.ltp
        snapshot = {"ema_fast": fast_last, "ema_slow": slow_last}

        crossed_up = fast_prev <= slow_prev and fast_last > slow_last
        crossed_down = fast_prev >= slow_prev and fast_last < slow_last

        if crossed_up:
            return StrategySignal(
                signal=Signal.BUY,
                strategy_name=self.name,
                raw_confidence=0.58,
                reason=f"EMA{fast_period}/EMA{slow_period} bullish cross on {target_symbol}",
                indicator_snapshot=snapshot,
                suggested_sl=ltp - sl_points,
                suggested_target=ltp + target_points,
            )

        if crossed_down:
            return StrategySignal(
                signal=Signal.SELL,
                strategy_name=self.name,
                raw_confidence=0.58,
                reason=f"EMA{fast_period}/EMA{slow_period} bearish cross on {target_symbol}",
                indicator_snapshot=snapshot,
                suggested_sl=ltp + sl_points,
                suggested_target=ltp - target_points,
            )

        return self._no_trade("no EMA cross", snapshot)
