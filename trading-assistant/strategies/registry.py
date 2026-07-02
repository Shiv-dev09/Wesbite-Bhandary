"""Name -> strategy class registry. New strategies register here and become
available to the engine/backtester purely through config, no other code
changes needed."""
from __future__ import annotations

from strategies.banknifty_scalping import BankNiftyScalpingStrategy
from strategies.base import StrategyBase
from strategies.cpr_breakout import CprBreakoutStrategy
from strategies.ema_trend_following import EmaTrendFollowingStrategy
from strategies.macd_confirmation import MacdConfirmationStrategy
from strategies.opening_range_breakout import OpeningRangeBreakoutStrategy
from strategies.option_momentum import OptionMomentumStrategy
from strategies.rsi_momentum import RsiMomentumStrategy
from strategies.supertrend import SupertrendStrategy
from strategies.volume_breakout import VolumeBreakoutStrategy
from strategies.vwap_reversal import VwapReversalStrategy

STRATEGY_REGISTRY: dict[str, type[StrategyBase]] = {
    OpeningRangeBreakoutStrategy.name: OpeningRangeBreakoutStrategy,
    VwapReversalStrategy.name: VwapReversalStrategy,
    EmaTrendFollowingStrategy.name: EmaTrendFollowingStrategy,
    VolumeBreakoutStrategy.name: VolumeBreakoutStrategy,
    CprBreakoutStrategy.name: CprBreakoutStrategy,
    SupertrendStrategy.name: SupertrendStrategy,
    RsiMomentumStrategy.name: RsiMomentumStrategy,
    MacdConfirmationStrategy.name: MacdConfirmationStrategy,
    OptionMomentumStrategy.name: OptionMomentumStrategy,
    BankNiftyScalpingStrategy.name: BankNiftyScalpingStrategy,
}


def get_strategy(name: str, params: dict | None = None) -> StrategyBase:
    if name not in STRATEGY_REGISTRY:
        raise KeyError(f"Unknown strategy '{name}'. Registered: {sorted(STRATEGY_REGISTRY)}")
    return STRATEGY_REGISTRY[name](params or {})


def all_strategy_names() -> list[str]:
    return sorted(STRATEGY_REGISTRY)
