"""Replays historical bars through the exact same
Strategy -> ConfirmationEngine -> RiskManager -> PositionSizer -> PaperBroker
pipeline used by the live-paper cycle (main.py run-cycle), differing only
in which MarketDataProvider is injected. This is what proves the
architecture: identical trading logic, backtest or live-paper."""
from __future__ import annotations

import bisect
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from backtest import metrics
from broker.backtest_data_provider import BacktestDataProvider
from broker.interface import OrderRequest
from broker.paper_broker import PaperBroker
from broker.slippage import SlippageModel
from config.schema import AppConfig
from indicators import atr as atr_ind
from indicators import vwap as vwap_ind
from indicators.types import Bar, InstrumentKind, MarketContext
from journal.db import JournalDB
from risk.daily_state import DailyState
from risk.position_sizer import PositionSizer
from risk.risk_manager import RiskManager
from risk.stop_target import StopTargetCalculator
from strategies.base import Signal
from strategies.confirmation import ConfirmationEngine
from strategies.registry import get_strategy
from utils.time_utils import is_at_or_after, trading_date


@dataclass
class BacktestResult:
    strategy_name: str
    symbol: str
    trade_pnls: list[float]
    total_pnl: float
    win_rate: float
    profit_factor: float
    expectancy: float
    max_drawdown: float
    sharpe_ratio: float
    trade_count: int
    rejections: dict[str, int] = field(default_factory=dict)


def _daily_ohlc_map(bars: list[Bar]) -> dict[date, tuple[float, float, float]]:
    groups: dict[date, list[Bar]] = defaultdict(list)
    for bar in bars:
        groups[bar.timestamp.date()].append(bar)
    return {d: (max(b.high for b in gb), min(b.low for b in gb), gb[-1].close) for d, gb in groups.items()}


def _session_bars(bars: list[Bar], current_time) -> list[Bar]:
    current_date = current_time.date()
    idx = len(bars)
    start = idx
    for i in range(idx - 1, -1, -1):
        if bars[i].timestamp.date() != current_date:
            break
        start = i
    return bars[start:idx]


class BacktestEngine:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def run(
        self,
        strategy_name: str,
        symbol: str,
        bars: list[Bar],
        lot_size: int = 1,
        instrument_kind: InstrumentKind = InstrumentKind.EQUITY,
    ) -> BacktestResult:
        market_data = BacktestDataProvider({symbol: bars})
        db = JournalDB(":memory:")
        slippage = SlippageModel(self.config.slippage_bps)
        stop_target_calc = StopTargetCalculator(
            self.config.risk_limits.min_risk_reward, self.config.risk_limits.ideal_risk_reward
        )
        broker = PaperBroker(
            db, market_data, slippage, stop_target_calc, self.config.capital.starting_capital, csv_path=None
        )
        risk_manager = RiskManager(self.config)
        position_sizer = PositionSizer()
        confirmation_engine = ConfirmationEngine(self.config.confirmation)

        strategy_cfg = self.config.strategies.get(strategy_name)
        strategy = get_strategy(strategy_name, strategy_cfg.params if strategy_cfg else {})

        daily_ohlc = _daily_ohlc_map(bars)
        sorted_dates = sorted(daily_ohlc)

        trade_pnls: list[float] = []
        equity_curve: list[float] = [self.config.capital.starting_capital]
        rejections: dict[str, int] = defaultdict(int)
        daily_state = DailyState(trade_date=bars[0].timestamp.date()) if bars else None

        start_index = max(strategy.required_history_bars, 1)
        for i in range(start_index, len(bars)):
            market_data.set_cursor(symbol, i)
            current_bars = market_data.get_bars(symbol)
            quote = market_data.get_quote(symbol)
            now = bars[i].timestamp
            if quote is None:
                continue

            current_date = trading_date(now)
            if daily_state is None or daily_state.trade_date != current_date:
                daily_state = DailyState(trade_date=current_date)

            atr_val = atr_ind.latest_atr(current_bars, 14) or 0.0
            session = _session_bars(current_bars, now)
            vwap_val = vwap_ind.session_vwap(session) or quote.ltp

            prev_idx = bisect.bisect_left(sorted_dates, current_date) - 1
            prev_high = prev_low = prev_close = None
            if prev_idx >= 0:
                prev_high, prev_low, prev_close = daily_ohlc[sorted_dates[prev_idx]]

            context = MarketContext(
                symbol=symbol,
                kind=instrument_kind,
                quote=quote,
                session_vwap=vwap_val,
                atr=atr_val,
                now=now,
                lot_size=lot_size,
                prev_day_high=prev_high,
                prev_day_low=prev_low,
                prev_day_close=prev_close,
            )

            stop_message = risk_manager.evaluate_daily_stop(daily_state, now)
            if stop_message:
                for result in broker.flatten_all(stop_message, now):
                    if result.pnl is not None:
                        trade_pnls.append(result.pnl)
                        risk_manager.register_trade_close(daily_state, result.pnl, now)
                equity_curve.append(self.config.capital.starting_capital + sum(trade_pnls))
                continue

            broker.update_trailing_stops({symbol: atr_val})
            for result in broker.check_exits(now):
                if result.pnl is not None:
                    trade_pnls.append(result.pnl)
                    risk_manager.register_trade_close(daily_state, result.pnl, now)

            if is_at_or_after(now, self.config.session_time.square_off_by):
                for result in broker.flatten_all("EOD_FLATTEN", now):
                    if result.pnl is not None:
                        trade_pnls.append(result.pnl)
                        risk_manager.register_trade_close(daily_state, result.pnl, now)
                equity_curve.append(self.config.capital.starting_capital + sum(trade_pnls))
                continue

            if not broker.get_open_positions():
                raw_signal = strategy.generate_signal(current_bars, context)
                if raw_signal.signal != Signal.NO_TRADE:
                    confirmed = confirmation_engine.evaluate(raw_signal, current_bars, context)
                    if confirmed.signal != Signal.NO_TRADE:
                        plan = stop_target_calc.build_plan(
                            confirmed.signal, quote.ltp, confirmed.suggested_sl, confirmed.suggested_target, atr_val
                        )
                        if plan is None:
                            rejections["risk_reward_not_met"] += 1
                        else:
                            risk_pct = self._risk_pct_for_confidence(confirmed.raw_confidence)
                            sizing = position_sizer.calculate(
                                self.config.capital.starting_capital,
                                plan.entry_price,
                                plan.initial_sl,
                                risk_pct,
                                lot_size,
                                broker.get_available_margin(),
                                self.config.safety_checks.min_available_margin_buffer_pct,
                            )
                            decision = risk_manager.can_enter_trade(
                                confirmed, daily_state, context, now, len(broker.get_open_positions()), sizing
                            )
                            if decision.allowed:
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
                                broker.place_simulated_order(order, now)
                            else:
                                rejections[decision.reason] += 1

            equity_curve.append(self.config.capital.starting_capital + sum(trade_pnls))

        if bars:
            for result in broker.flatten_all("BACKTEST_END", bars[-1].timestamp):
                if result.pnl is not None:
                    trade_pnls.append(result.pnl)

        db.close()

        return BacktestResult(
            strategy_name=strategy.name,
            symbol=symbol,
            trade_pnls=trade_pnls,
            total_pnl=sum(trade_pnls),
            win_rate=metrics.win_rate(trade_pnls),
            profit_factor=metrics.profit_factor(trade_pnls),
            expectancy=metrics.expectancy(trade_pnls),
            max_drawdown=metrics.max_drawdown(equity_curve),
            sharpe_ratio=metrics.sharpe_ratio(trade_pnls),
            trade_count=len(trade_pnls),
            rejections=dict(rejections),
        )

    def _risk_pct_for_confidence(self, confidence: float) -> float:
        """Scales risk-per-trade linearly between the configured min and
        max risk% based on confirmation confidence -- higher-conviction
        setups get (slightly) more risk budget, never more than the
        configured ceiling."""
        lo = self.config.capital.risk_per_trade_pct_min
        hi = self.config.capital.risk_per_trade_pct_max
        return lo + max(0.0, min(1.0, confidence)) * (hi - lo)
