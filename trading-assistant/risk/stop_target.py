"""Every trade carries an initial SL, a trailing SL rule, and a profit
target sized to the configured minimum (1:2 floor, 1:3 ideal) risk:reward."""
from __future__ import annotations

from dataclasses import dataclass

from strategies.base import Signal


@dataclass(frozen=True)
class TradePlan:
    entry_price: float
    initial_sl: float
    target: float
    risk_reward: float


class StopTargetCalculator:
    def __init__(self, min_risk_reward: float = 2.0, ideal_risk_reward: float = 3.0) -> None:
        self.min_risk_reward = min_risk_reward
        self.ideal_risk_reward = ideal_risk_reward

    def build_plan(
        self,
        direction: Signal,
        entry_price: float,
        suggested_sl: float | None,
        suggested_target: float | None,
        atr: float,
    ) -> TradePlan | None:
        """Builds a trade plan from a strategy's suggested SL/target,
        falling back to an ATR-based SL if the strategy didn't provide
        one, and always enforcing at least the minimum R:R by extending
        the target if needed."""
        sl = suggested_sl
        if sl is None:
            sl = entry_price - atr * 1.5 if direction == Signal.BUY else entry_price + atr * 1.5

        risk = abs(entry_price - sl)
        if risk <= 0:
            return None

        target = suggested_target
        min_target_distance = risk * self.min_risk_reward
        if direction == Signal.BUY:
            min_target = entry_price + min_target_distance
            if target is None or target < min_target:
                target = entry_price + risk * self.ideal_risk_reward
        else:
            min_target = entry_price - min_target_distance
            if target is None or target > min_target:
                target = entry_price - risk * self.ideal_risk_reward

        reward = abs(target - entry_price)
        rr = reward / risk if risk else 0.0
        if rr < self.min_risk_reward:
            return None

        return TradePlan(entry_price=entry_price, initial_sl=sl, target=target, risk_reward=rr)

    def update_trailing_stop(
        self,
        direction: Signal,
        current_price: float,
        current_sl: float,
        atr: float,
        trail_multiplier: float = 1.5,
    ) -> float:
        """Trailing SL only ever moves in the trade's favor, never back
        toward the entry."""
        candidate = current_price - atr * trail_multiplier if direction == Signal.BUY else current_price + atr * trail_multiplier
        if direction == Signal.BUY:
            return max(current_sl, candidate)
        return min(current_sl, candidate)

    def partial_exit_levels(
        self, direction: Signal, entry_price: float, target: float, portions: tuple[float, ...] = (0.5, 0.5)
    ) -> list[tuple[float, float]]:
        """Splits the distance to target into partial-exit price levels,
        each paired with the fraction of the position to close there.
        e.g. (0.5, 0.5) exits half at the midpoint and the rest at target."""
        if abs(sum(portions) - 1.0) > 1e-6:
            raise ValueError("portions must sum to 1.0")

        total_distance = target - entry_price
        levels: list[tuple[float, float]] = []
        cumulative_fraction = 0.0
        for fraction in portions:
            cumulative_fraction += fraction
            price = entry_price + total_distance * cumulative_fraction
            levels.append((price, fraction))
        return levels
