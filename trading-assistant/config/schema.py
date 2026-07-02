"""Typed configuration schema for the trading assistant.

All trading parameters (capital, risk limits, session times, per-strategy
params, confirmation weights) live in config/default.yaml and are loaded
into these dataclasses by config/loader.py. Nothing here is a live trading
default meant to be hand-edited in code -- edit the YAML instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CapitalConfig:
    starting_capital: float
    daily_profit_target: float
    daily_max_loss: float
    max_capital_deployed_pct: float  # 0-100, fraction of capital allowed deployed at once
    risk_per_trade_pct_min: float    # 0.5
    risk_per_trade_pct_max: float    # 1.0

    def __post_init__(self) -> None:
        if self.starting_capital <= 0:
            raise ValueError("starting_capital must be positive")
        if self.daily_max_loss <= 0:
            raise ValueError("daily_max_loss must be positive")
        if not (0.0 < self.risk_per_trade_pct_min <= self.risk_per_trade_pct_max <= 5.0):
            raise ValueError("risk_per_trade_pct_min/max out of sane range (0, 5]")
        if not (0.0 < self.max_capital_deployed_pct <= 100.0):
            raise ValueError("max_capital_deployed_pct must be in (0, 100]")


@dataclass(frozen=True)
class RiskLimitsConfig:
    max_open_positions: int
    max_trades_per_day: int
    consecutive_loss_pause_minutes: int
    consecutive_losses_trigger: int
    min_risk_reward: float           # 1:2 floor
    ideal_risk_reward: float         # 1:3 target

    def __post_init__(self) -> None:
        if self.max_open_positions < 1:
            raise ValueError("max_open_positions must be >= 1")
        if self.max_trades_per_day < 1:
            raise ValueError("max_trades_per_day must be >= 1")
        if self.min_risk_reward < 1.0:
            raise ValueError("min_risk_reward must be >= 1.0")


@dataclass(frozen=True)
class SessionTimeConfig:
    scan_start: str      # "09:15"
    first_trade: str     # "09:20"
    no_new_entries_after: str  # "14:45"
    square_off_by: str   # "15:15"


@dataclass(frozen=True)
class SafetyChecksConfig:
    max_spread_pct: float          # reject if (ask-bid)/ltp exceeds this
    min_volume: int                # reject if traded volume below this
    max_atr_pct: float             # reject if ATR% of price exceeds this (volatility too high)
    circuit_limit_buffer_pct: float  # reject if LTP within this % of upper/lower circuit
    min_available_margin_buffer_pct: float  # keep this % of margin unused as safety buffer


@dataclass(frozen=True)
class OptionsConfig:
    strike_selection: str          # "ATM" or "ITM1"
    min_open_interest: int
    min_volume: int
    min_delta: float
    max_days_to_expiry: int
    risk_free_rate: float           # for Black-Scholes greeks


@dataclass(frozen=True)
class ConfirmationConfig:
    threshold: float                # 0-1 minimum blended confidence to allow a trade
    weights: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (0.0 <= self.threshold <= 1.0):
            raise ValueError("confirmation.threshold must be within [0, 1]")


@dataclass(frozen=True)
class StrategyParamConfig:
    enabled: bool
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class WatchlistConfig:
    indices: list[str] = field(default_factory=list)
    equities: list[str] = field(default_factory=list)
    min_price: float = 100.0


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    log_dir: str = "logs"
    max_bytes: int = 5_000_000
    backup_count: int = 5


@dataclass(frozen=True)
class AppConfig:
    capital: CapitalConfig
    risk_limits: RiskLimitsConfig
    session_time: SessionTimeConfig
    safety_checks: SafetyChecksConfig
    options: OptionsConfig
    confirmation: ConfirmationConfig
    watchlist: WatchlistConfig
    logging: LoggingConfig
    strategies: dict[str, StrategyParamConfig] = field(default_factory=dict)
    db_path: str = "logs/trading_assistant.sqlite3"
    slippage_bps: float = 5.0
