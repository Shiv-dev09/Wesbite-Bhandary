"""Multi-confirmation scoring layer.

No strategy is allowed to trade on a single indicator. Every raw
StrategySignal a strategy produces is re-scored here across seven
independent dimensions (trend, momentum, volume, price action, VWAP, EMA
alignment, support/resistance), blended with the strategy's own
raw_confidence, and downgraded to NO_TRADE if the blended confidence falls
below the configured threshold. This is the single place "never enter
based on a single indicator" is enforced, so individual strategy files
stay simple.
"""
from __future__ import annotations

from dataclasses import dataclass

from config.schema import ConfirmationConfig
from indicators import macd as macd_ind
from indicators import moving_averages as ma
from indicators import rsi as rsi_ind
from indicators import support_resistance as sr
from indicators import volume_profile as vol
from indicators.types import Bar, MarketContext
from strategies.base import Signal, StrategySignal

_DIRECTIONAL_SIGNALS = (Signal.BUY, Signal.SELL)


@dataclass(frozen=True)
class ConfirmationBreakdown:
    trend: float
    momentum: float
    volume: float
    price_action: float
    vwap: float
    ema: float
    support_resistance: float
    blended: float
    final_confidence: float


def _closes(bars: list[Bar]) -> list[float]:
    return [b.close for b in bars]


def _score_trend(bars: list[Bar], direction: Signal) -> float:
    """EMA(9) vs EMA(21) slope alignment with the proposed direction."""
    closes = _closes(bars)
    if len(closes) < 21:
        return 0.0
    fast = ma.ema(closes, 9)
    slow = ma.ema(closes, 21)
    fast_last = next((v for v in reversed(fast) if v is not None), None)
    slow_last = next((v for v in reversed(slow) if v is not None), None)
    if fast_last is None or slow_last is None:
        return 0.0
    bullish = fast_last > slow_last
    aligned = bullish if direction == Signal.BUY else not bullish
    if not aligned:
        return 0.0
    spread_pct = abs(fast_last - slow_last) / slow_last * 100.0 if slow_last else 0.0
    return min(1.0, 0.5 + spread_pct * 5)


def _score_momentum(bars: list[Bar], direction: Signal) -> float:
    """RSI positioned in the direction's favor + MACD histogram sign."""
    closes = _closes(bars)
    if len(closes) < 26:
        return 0.0
    r = rsi_ind.latest_rsi(closes, 14)
    _, _, hist = macd_ind.latest_macd(closes)
    score = 0.0
    if r is not None:
        if direction == Signal.BUY and r > 50:
            score += min(1.0, (r - 50) / 30) * 0.5
        elif direction == Signal.SELL and r < 50:
            score += min(1.0, (50 - r) / 30) * 0.5
    if hist is not None:
        if direction == Signal.BUY and hist > 0:
            score += 0.5
        elif direction == Signal.SELL and hist < 0:
            score += 0.5
    return min(1.0, score)


def _score_volume(bars: list[Bar]) -> float:
    rv = vol.relative_volume(bars, lookback=20)
    if rv is None:
        return 0.0
    return min(1.0, max(0.0, (rv - 1.0) / 1.5))


def _score_price_action(bars: list[Bar], direction: Signal) -> float:
    """Where the latest close sits within its own bar range -- a close
    near the high (for BUY) or low (for SELL) signals conviction."""
    if not bars:
        return 0.0
    last = bars[-1]
    bar_range = last.high - last.low
    if bar_range <= 0:
        return 0.3
    close_position = (last.close - last.low) / bar_range
    return close_position if direction == Signal.BUY else (1.0 - close_position)


def _score_vwap(context: MarketContext, direction: Signal) -> float:
    if not context.session_vwap:
        return 0.0
    ltp = context.quote.ltp
    diff_pct = (ltp - context.session_vwap) / context.session_vwap * 100.0
    if direction == Signal.BUY:
        return min(1.0, max(0.0, 0.5 + diff_pct * 2))
    return min(1.0, max(0.0, 0.5 - diff_pct * 2))


def _score_ema(bars: list[Bar], context: MarketContext, direction: Signal) -> float:
    closes = _closes(bars)
    if len(closes) < 21:
        return 0.0
    ema21 = ma.latest_ema(closes, 21)
    if ema21 is None:
        return 0.0
    ltp = context.quote.ltp
    above = ltp > ema21
    return 1.0 if (above if direction == Signal.BUY else not above) else 0.0


def _score_support_resistance(bars: list[Bar], context: MarketContext, direction: Signal) -> float:
    resistance, support = sr.nearest_levels(context.quote.ltp, bars, lookback=3)
    ltp = context.quote.ltp
    if direction == Signal.BUY:
        # Confidence is higher when price has cleanly broken above resistance
        # or is bouncing cleanly off support, not stuck mid-range.
        if resistance is not None and ltp > resistance:
            return 0.8
        if support is not None and ltp > 0:
            dist_pct = abs(ltp - support) / ltp * 100.0
            return max(0.0, 0.6 - dist_pct * 0.1)
        return 0.3
    else:
        if support is not None and ltp < support:
            return 0.8
        if resistance is not None and ltp > 0:
            dist_pct = abs(resistance - ltp) / ltp * 100.0
            return max(0.0, 0.6 - dist_pct * 0.1)
        return 0.3


class ConfirmationEngine:
    def __init__(self, config: ConfirmationConfig) -> None:
        self.config = config

    def evaluate(self, raw: StrategySignal, bars: list[Bar], context: MarketContext) -> StrategySignal:
        if raw.signal not in _DIRECTIONAL_SIGNALS:
            return raw

        breakdown = self.score(raw.signal, bars, context)
        # Blend the strategy's own conviction with the independent
        # multi-dimension confirmation score -- neither alone is enough.
        final_confidence = 0.4 * raw.raw_confidence + 0.6 * breakdown.blended

        if final_confidence < self.config.threshold:
            return StrategySignal(
                signal=Signal.NO_TRADE,
                strategy_name=raw.strategy_name,
                raw_confidence=final_confidence,
                reason=(
                    f"confirmation confidence {final_confidence:.2f} below threshold "
                    f"{self.config.threshold:.2f} (raw={raw.reason})"
                ),
                indicator_snapshot={**raw.indicator_snapshot, "confirmation_blended": breakdown.blended},
            )

        return StrategySignal(
            signal=raw.signal,
            strategy_name=raw.strategy_name,
            raw_confidence=final_confidence,
            reason=raw.reason,
            indicator_snapshot={**raw.indicator_snapshot, "confirmation_blended": breakdown.blended},
            suggested_sl=raw.suggested_sl,
            suggested_target=raw.suggested_target,
        )

    def score(self, direction: Signal, bars: list[Bar], context: MarketContext) -> ConfirmationBreakdown:
        w = self.config.weights
        trend = _score_trend(bars, direction)
        momentum = _score_momentum(bars, direction)
        volume = _score_volume(bars)
        price_action = _score_price_action(bars, direction)
        vwap = _score_vwap(context, direction)
        ema_score = _score_ema(bars, context, direction)
        support_resistance = _score_support_resistance(bars, context, direction)

        blended = (
            trend * w.get("trend", 0)
            + momentum * w.get("momentum", 0)
            + volume * w.get("volume", 0)
            + price_action * w.get("price_action", 0)
            + vwap * w.get("vwap", 0)
            + ema_score * w.get("ema", 0)
            + support_resistance * w.get("support_resistance", 0)
        )

        return ConfirmationBreakdown(
            trend=trend,
            momentum=momentum,
            volume=volume,
            price_action=price_action,
            vwap=vwap,
            ema=ema_score,
            support_resistance=support_resistance,
            blended=blended,
            final_confidence=blended,
        )
