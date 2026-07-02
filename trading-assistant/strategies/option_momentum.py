"""Option Momentum: generates a directional call/put bias from the
underlying's own price momentum. BUY means "buy calls" (or sell puts),
SELL means "buy puts" -- actual strike selection (ATM/ITM1, OI/volume/
delta filters) happens downstream in broker/instruments.py + risk sizing,
not here. This strategy only decides direction + conviction on the
underlying, and requires realized volatility (ATR%) to be in a reasonable
band so we're not paying for options on a dead tape."""
from __future__ import annotations

from indicators import atr as atr_ind
from indicators import moving_averages as ma
from indicators.types import Bar, MarketContext
from strategies.base import Signal, StrategyBase, StrategySignal


class OptionMomentumStrategy(StrategyBase):
    name = "option_momentum"
    required_history_bars = 25

    def generate_signal(self, bars: list[Bar], context: MarketContext) -> StrategySignal:
        ema_period = int(self.params.get("underlying_ema_period", 9))
        min_move_pct = float(self.params.get("min_underlying_move_pct", 0.15))
        iv_lookback = int(self.params.get("iv_lookback_bars", 20))

        if not self.has_sufficient_history(bars):
            return self._no_trade("insufficient history")

        closes = [b.close for b in bars]
        underlying_ema = ma.latest_ema(closes, ema_period)
        if underlying_ema is None:
            return self._no_trade("EMA not ready")

        last = bars[-1]
        prev = bars[-2]
        move_pct = (last.close - prev.close) / prev.close * 100.0 if prev.close else 0.0

        atr_series = atr_ind.atr(bars, 14)
        recent_atr_vals = [v for v in atr_series[-iv_lookback:] if v is not None]
        avg_atr_pct = None
        if recent_atr_vals and last.close:
            avg_atr_pct = (sum(recent_atr_vals) / len(recent_atr_vals)) / last.close * 100.0

        snapshot = {"underlying_ema": underlying_ema, "move_pct": move_pct, "avg_atr_pct": avg_atr_pct or 0.0}

        # Skip a dead tape: without enough realized movement, option premium
        # is dominated by theta decay rather than directional payoff.
        if avg_atr_pct is not None and avg_atr_pct < 0.15:
            return self._no_trade("underlying volatility too low for options momentum", snapshot)

        ltp = context.quote.ltp
        atr_val = atr_ind.latest_atr(bars, 14) or (context.atr or 0.0)

        if ltp > underlying_ema and move_pct >= min_move_pct:
            sl = ltp - atr_val * 1.0
            target = ltp + atr_val * 1.0 * 2.0
            return StrategySignal(
                signal=Signal.BUY,
                strategy_name=self.name,
                raw_confidence=0.6,
                reason=f"underlying above EMA{ema_period} with {move_pct:.2f}% up move -- call bias",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        if ltp < underlying_ema and move_pct <= -min_move_pct:
            sl = ltp + atr_val * 1.0
            target = ltp - atr_val * 1.0 * 2.0
            return StrategySignal(
                signal=Signal.SELL,
                strategy_name=self.name,
                raw_confidence=0.6,
                reason=f"underlying below EMA{ema_period} with {move_pct:.2f}% down move -- put bias",
                indicator_snapshot=snapshot,
                suggested_sl=sl,
                suggested_target=target,
            )

        return self._no_trade("no qualifying underlying momentum", snapshot)
