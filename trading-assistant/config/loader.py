"""Loads config/default.yaml (with optional .env overrides for paths/log
level only -- never for trading parameters) into a validated AppConfig."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from config.schema import (
    AppConfig,
    CapitalConfig,
    ConfirmationConfig,
    LoggingConfig,
    OptionsConfig,
    RiskLimitsConfig,
    SafetyChecksConfig,
    SessionTimeConfig,
    StrategyParamConfig,
    WatchlistConfig,
)

DEFAULT_CONFIG_PATH = Path(__file__).parent / "default.yaml"


def _load_dotenv_overrides() -> dict[str, str]:
    """Reads a .env file (if present) at the project root without adding a
    hard dependency on python-dotenv's auto-loading side effects."""
    env_path = Path(__file__).parent.parent / ".env"
    overrides: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            overrides[key.strip()] = value.strip().strip('"').strip("'")
    return overrides


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    env_overrides = {**_load_dotenv_overrides(), **os.environ}

    capital = CapitalConfig(**raw["capital"])
    risk_limits = RiskLimitsConfig(**raw["risk_limits"])
    session_time = SessionTimeConfig(**raw["session_time"])
    safety_checks = SafetyChecksConfig(**raw["safety_checks"])
    options = OptionsConfig(**raw["options"])
    confirmation = ConfirmationConfig(
        threshold=raw["confirmation"]["threshold"],
        weights=dict(raw["confirmation"].get("weights", {})),
    )
    watchlist = WatchlistConfig(**raw.get("watchlist", {}))

    logging_raw = dict(raw.get("logging", {}))
    if "TRADING_ASSISTANT_LOG_LEVEL" in env_overrides:
        logging_raw["level"] = env_overrides["TRADING_ASSISTANT_LOG_LEVEL"]
    logging_cfg = LoggingConfig(**logging_raw)

    strategies_raw = raw.get("strategies", {})
    strategies = {
        name: StrategyParamConfig(
            enabled=bool(cfg.get("enabled", True)),
            params=dict(cfg.get("params", {})),
        )
        for name, cfg in strategies_raw.items()
    }

    db_path = env_overrides.get("TRADING_ASSISTANT_DB_PATH", raw.get("db_path", "logs/trading_assistant.sqlite3"))

    weight_sum = sum(confirmation.weights.values())
    if confirmation.weights and not (0.95 <= weight_sum <= 1.05):
        raise ValueError(f"confirmation.weights must sum to ~1.0, got {weight_sum}")

    return AppConfig(
        capital=capital,
        risk_limits=risk_limits,
        session_time=session_time,
        safety_checks=safety_checks,
        options=options,
        confirmation=confirmation,
        watchlist=watchlist,
        logging=logging_cfg,
        strategies=strategies,
        db_path=db_path,
        slippage_bps=float(raw.get("slippage_bps", 5.0)),
    )
