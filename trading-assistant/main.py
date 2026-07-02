"""CLI entrypoint for the trading assistant.

Subcommands:
  init-db            create/upgrade the local SQLite schema
  backtest            run one strategy against cached historical bars
  backtest-compare     run several strategies against the same symbol and print a comparison table
  run-cycle            run one live-paper engine tick (signals -> confirmation -> risk -> simulated
                       fills -> journal -> dashboard), reading only the local snapshot DB
  dashboard            render the current dashboard state without advancing the engine

This system is PAPER TRADING ONLY -- see README.md. No subcommand here
ever places, modifies, or cancels a real broker order.
"""
from __future__ import annotations

import argparse
import logging

from backtest.data_cache import load_bars
from backtest.engine import BacktestEngine
from backtest.report import render_table
from broker.external_feed_provider import ExternalFeedDataProvider
from broker.interface import OrderRequest
from broker.paper_broker import PaperBroker
from broker.slippage import SlippageModel
from config.loader import load_config
from config.schema import AppConfig
from dashboard.renderer import DashboardData, DashboardRenderer
from indicators import atr as atr_ind
from indicators import vwap as vwap_ind
from indicators.types import InstrumentKind, MarketContext
from journal.db import JournalDB
from risk.daily_state import DailyState
from risk.position_sizer import PositionSizer
from risk.risk_manager import RiskManager
from risk.stop_target import StopTargetCalculator
from strategies.base import Signal, StrategySignal
from strategies.confirmation import ConfirmationEngine
from strategies.registry import STRATEGY_REGISTRY, get_strategy
from utils.logging_setup import setup_logging
from utils.time_utils import is_at_or_after, now_ist, trading_date
from utils.validation import filter_valid_bars, is_valid_quote

logger = logging.getLogger("trading_assistant")


def cmd_init_db(args: argparse.Namespace, config: AppConfig) -> None:
    db = JournalDB(config.db_path)
    db.close()
    print(f"Initialized database at {config.db_path}")


def cmd_backtest(args: argparse.Namespace, config: AppConfig) -> None:
    db = JournalDB(config.db_path)
    try:
        bars_by_symbol = load_bars(db, [args.symbol], args.interval, args.from_ts, args.to_ts)
    finally:
        db.close()

    bars = filter_valid_bars(bars_by_symbol.get(args.symbol, []))
    if not bars:
        print(f"No cached bars for {args.symbol} (interval={args.interval}). Ingest historical data first.")
        return

    engine = BacktestEngine(config)
    kind = InstrumentKind.INDEX if args.symbol in config.watchlist.indices else InstrumentKind.EQUITY
    result = engine.run(args.strategy, args.symbol, bars, lot_size=args.lot_size, instrument_kind=kind)

    print(f"Strategy: {result.strategy_name}  Symbol: {result.symbol}")
    print(f"Trades: {result.trade_count}  Total PnL: {result.total_pnl:.2f}  Win rate: {result.win_rate:.1f}%")
    print(f"Profit factor: {result.profit_factor:.2f}  Expectancy: {result.expectancy:.2f}")
    print(f"Max drawdown: {result.max_drawdown:.2f}  Sharpe: {result.sharpe_ratio:.2f}")
    if result.rejections:
        print("Top rejection reasons:")
        for reason, count in sorted(result.rejections.items(), key=lambda kv: -kv[1])[:5]:
            print(f"  {count:4d}  {reason}")


def cmd_backtest_compare(args: argparse.Namespace, config: AppConfig) -> None:
    strategy_names = args.strategies.split(",") if args.strategies else sorted(STRATEGY_REGISTRY)

    db = JournalDB(config.db_path)
    try:
        bars_by_symbol = load_bars(db, [args.symbol], args.interval, args.from_ts, args.to_ts)
    finally:
        db.close()

    bars = filter_valid_bars(bars_by_symbol.get(args.symbol, []))
    if not bars:
        print(f"No cached bars for {args.symbol} (interval={args.interval}). Ingest historical data first.")
        return

    engine = BacktestEngine(config)
    kind = InstrumentKind.INDEX if args.symbol in config.watchlist.indices else InstrumentKind.EQUITY
    results = [
        engine.run(name, args.symbol, bars, lot_size=args.lot_size, instrument_kind=kind) for name in strategy_names
    ]

    from rich.console import Console

    Console().print(render_table(results))


def _watchlist_symbols(config: AppConfig) -> list[tuple[str, InstrumentKind]]:
    symbols = [(s, InstrumentKind.INDEX) for s in config.watchlist.indices]
    symbols += [(s, InstrumentKind.EQUITY) for s in config.watchlist.equities]
    return symbols


def _load_daily_state(db: JournalDB, trade_date) -> DailyState:
    """Reconstructs today's DailyState from the journal DB. Each run-cycle
    invocation is a fresh process, so consecutive-loss streaks, trade
    counts, and realized PnL are all re-derived from persisted trades
    rather than kept in memory across cycles. Note: the consecutive-loss
    pause timer itself does not survive a process restart mid-pause --
    a documented limitation of this poll-driven architecture."""
    rows = db.get_trades_for_date(trade_date.isoformat())
    state = DailyState(trade_date=trade_date)
    consecutive = 0
    for row in rows:
        if row["status"] != "CLOSED":
            continue
        pnl = row["pnl"] or 0.0
        state.realized_pnl += pnl
        state.trades_today += 1
        if pnl > 0:
            state.wins += 1
            consecutive = 0
        else:
            state.losses += 1
            consecutive += 1
    state.consecutive_losses = consecutive
    return state


def _build_broker(config: AppConfig, db: JournalDB, market_data: ExternalFeedDataProvider, csv_path: str | None) -> PaperBroker:
    slippage = SlippageModel(config.slippage_bps)
    stop_target_calc = StopTargetCalculator(config.risk_limits.min_risk_reward, config.risk_limits.ideal_risk_reward)
    broker = PaperBroker(db, market_data, slippage, stop_target_calc, config.capital.starting_capital, csv_path=csv_path)
    broker.restore_open_positions(db.get_open_trades())
    return broker


def cmd_run_cycle(args: argparse.Namespace, config: AppConfig) -> None:
    db = JournalDB(config.db_path)
    market_data = ExternalFeedDataProvider(db)
    broker = _build_broker(config, db, market_data, csv_path="logs/trade_journal.csv")

    risk_manager = RiskManager(config)
    position_sizer = PositionSizer()
    confirmation_engine = ConfirmationEngine(config.confirmation)
    stop_target_calc = stop_target_calc_for(config)

    now = now_ist()
    today = trading_date(now)
    daily_state = _load_daily_state(db, today)

    stop_message = risk_manager.evaluate_daily_stop(daily_state, now)
    if stop_message:
        for result in broker.flatten_all(stop_message, now):
            if result.pnl is not None:
                risk_manager.register_trade_close(daily_state, result.pnl, now)
        print(stop_message)

    if is_at_or_after(now, config.session_time.square_off_by):
        for result in broker.flatten_all("EOD_FLATTEN", now):
            if result.pnl is not None:
                risk_manager.register_trade_close(daily_state, result.pnl, now)

    signals: dict[str, StrategySignal] = {}

    for symbol, kind in _watchlist_symbols(config):
        quote = market_data.get_quote(symbol)
        if not is_valid_quote(quote):
            continue
        bars = filter_valid_bars(market_data.get_bars(symbol, lookback=200))
        if not bars:
            continue

        atr_val = atr_ind.latest_atr(bars, 14) or 0.0
        session = vwap_ind.session_bars_only(bars, now)
        vwap_val = vwap_ind.session_vwap(session) or quote.ltp
        # Equity lot size is 1; index-symbol signals (option_momentum,
        # banknifty_scalping) currently simulate fills at the index LTP
        # itself as a directional proxy rather than routing through an
        # actual option contract -- see README's "Known simplifications".
        lot_size = 1

        context = MarketContext(
            symbol=symbol, kind=kind, quote=quote, session_vwap=vwap_val, atr=atr_val, now=now, lot_size=lot_size,
        )

        broker.update_trailing_stops({symbol: atr_val})

        if daily_state.trading_disabled:
            continue

        for strategy_name, strategy_cfg in config.strategies.items():
            if not strategy_cfg.enabled:
                continue
            strategy = get_strategy(strategy_name, strategy_cfg.params)
            if len(bars) < strategy.required_history_bars:
                continue

            raw_signal = strategy.generate_signal(bars, context)
            signal_key = f"{strategy_name}:{symbol}"
            if raw_signal.signal == Signal.NO_TRADE:
                signals[signal_key] = raw_signal
                continue

            confirmed = confirmation_engine.evaluate(raw_signal, bars, context)
            signals[signal_key] = confirmed
            if confirmed.signal == Signal.NO_TRADE:
                continue

            plan = stop_target_calc.build_plan(
                confirmed.signal, quote.ltp, confirmed.suggested_sl, confirmed.suggested_target, atr_val
            )
            if plan is None:
                continue

            risk_pct = config.capital.risk_per_trade_pct_min + confirmed.raw_confidence * (
                config.capital.risk_per_trade_pct_max - config.capital.risk_per_trade_pct_min
            )
            sizing = position_sizer.calculate(
                config.capital.starting_capital,
                plan.entry_price,
                plan.initial_sl,
                risk_pct,
                lot_size,
                broker.get_available_margin(),
                config.safety_checks.min_available_margin_buffer_pct,
            )
            decision = risk_manager.can_enter_trade(
                confirmed, daily_state, context, now, len(broker.get_open_positions()), sizing
            )
            if not decision.allowed:
                logger.info("Trade rejected for %s/%s: %s", strategy_name, symbol, decision.reason)
                continue

            order = OrderRequest(
                symbol=symbol,
                side=confirmed.signal,
                quantity=sizing.quantity,
                strategy=strategy.name,
                initial_sl=plan.initial_sl,
                target=plan.target,
                confidence_score=confirmed.raw_confidence,
                indicator_snapshot=confirmed.indicator_snapshot,
            )
            result = broker.place_simulated_order(order, now)
            if result.accepted:
                logger.info(
                    "Opened %s %s x%s @ %.2f (%s)",
                    confirmed.signal.value, symbol, sizing.quantity, result.fill_price, strategy.name,
                )

    for result in broker.check_exits(now):
        if result.pnl is not None:
            risk_manager.register_trade_close(daily_state, result.pnl, now)

    stop_message_after = risk_manager.evaluate_daily_stop(daily_state, now)
    if stop_message_after:
        for result in broker.flatten_all(stop_message_after, now):
            if result.pnl is not None:
                risk_manager.register_trade_close(daily_state, result.pnl, now)
        print(stop_message_after)

    db.upsert_daily_summary(
        today.isoformat(), daily_state.realized_pnl, daily_state.trades_today,
        daily_state.wins, daily_state.losses, daily_state.target_hit, daily_state.loss_limit_hit,
    )

    dashboard = DashboardRenderer(config)
    data = DashboardData(
        daily_state=daily_state,
        open_positions=broker.get_open_positions(),
        recent_trades=db.get_trades_for_date(today.isoformat()),
        strategy_signals=signals,
        available_margin=broker.get_available_margin(),
        now=now,
    )
    dashboard.render(data)
    db.close()


def stop_target_calc_for(config: AppConfig) -> StopTargetCalculator:
    return StopTargetCalculator(config.risk_limits.min_risk_reward, config.risk_limits.ideal_risk_reward)


def cmd_dashboard(args: argparse.Namespace, config: AppConfig) -> None:
    db = JournalDB(config.db_path)
    market_data = ExternalFeedDataProvider(db)
    broker = _build_broker(config, db, market_data, csv_path=None)

    now = now_ist()
    today = trading_date(now)
    daily_state = _load_daily_state(db, today)

    dashboard = DashboardRenderer(config)
    data = DashboardData(
        daily_state=daily_state,
        open_positions=broker.get_open_positions(),
        recent_trades=db.get_trades_for_date(today.isoformat()),
        strategy_signals={},
        available_margin=broker.get_available_margin(),
        now=now,
    )
    dashboard.render(data)
    db.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NSE intraday paper-trading assistant (decision support only).")
    parser.add_argument("--config", type=str, default=None, help="Path to config YAML (defaults to config/default.yaml)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Create/upgrade the local SQLite schema")

    p_backtest = sub.add_parser("backtest", help="Run one strategy against cached historical bars")
    p_backtest.add_argument("--strategy", required=True, choices=sorted(STRATEGY_REGISTRY))
    p_backtest.add_argument("--symbol", required=True)
    p_backtest.add_argument(
        "--interval", default="minute",
        help="Bar interval to replay. Must be 'minute' (or another intraday interval) for "
             "session-time gating (09:15-15:15) to produce any trades -- 'day' bars carry a "
             "midnight timestamp that always falls outside the trading session.",
    )
    p_backtest.add_argument("--from-ts", dest="from_ts", default=None)
    p_backtest.add_argument("--to-ts", dest="to_ts", default=None)
    p_backtest.add_argument("--lot-size", type=int, default=1)

    p_compare = sub.add_parser("backtest-compare", help="Compare multiple strategies on the same symbol")
    p_compare.add_argument("--strategies", default=None, help="Comma-separated strategy names; default = all")
    p_compare.add_argument("--symbol", required=True)
    p_compare.add_argument(
        "--interval", default="minute",
        help="Bar interval to replay -- see `backtest --interval` for why this should stay intraday.",
    )
    p_compare.add_argument("--from-ts", dest="from_ts", default=None)
    p_compare.add_argument("--to-ts", dest="to_ts", default=None)
    p_compare.add_argument("--lot-size", type=int, default=1)

    sub.add_parser("run-cycle", help="Run one live-paper engine tick (reads local snapshot DB only, never MCP)")
    sub.add_parser("dashboard", help="Render current dashboard state without advancing the engine")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(args.config)
    setup_logging(config.logging)

    commands = {
        "init-db": cmd_init_db,
        "backtest": cmd_backtest,
        "backtest-compare": cmd_backtest_compare,
        "run-cycle": cmd_run_cycle,
        "dashboard": cmd_dashboard,
    }
    commands[args.command](args, config)


if __name__ == "__main__":
    main()
