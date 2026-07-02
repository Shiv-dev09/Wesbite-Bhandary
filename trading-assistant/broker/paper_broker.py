"""The sole concrete broker in this project. Places, tracks, and closes
SIMULATED orders only: fills are computed from a MarketDataProvider quote
plus a SlippageModel, and persisted to the local SQLite journal (+ CSV
mirror). This module deliberately has zero import of, and never
references, any live Kite order-mutation tool -- no place_order,
modify_order, cancel_order, place_gtt_order, modify_gtt_order, or
delete_gtt_order anywhere in this file or anything it imports.
tests/test_broker/test_no_live_order_imports.py statically scans this
package for those identifiers as a regression guard, so a future change
can't silently wire in live execution.
"""
from __future__ import annotations

from datetime import datetime

from broker.interface import BrokerInterface, OrderRequest, OrderResult, Position
from broker.market_data import MarketDataProvider
from broker.slippage import SlippageModel
from journal import csv_export
from journal.db import JournalDB
from journal.models import Trade
from risk.stop_target import StopTargetCalculator
from strategies.base import Signal


class PaperBroker(BrokerInterface):
    def __init__(
        self,
        db: JournalDB,
        market_data: MarketDataProvider,
        slippage: SlippageModel,
        stop_target_calc: StopTargetCalculator,
        starting_capital: float,
        csv_path: str | None = "logs/trade_journal.csv",
    ) -> None:
        self.db = db
        self.market_data = market_data
        self.slippage = slippage
        self.stop_target_calc = stop_target_calc
        self.starting_capital = starting_capital
        self.csv_path = csv_path
        self._open_positions: dict[int, Position] = {}
        self._deployed_capital = 0.0

    def get_available_margin(self) -> float:
        return max(0.0, self.starting_capital - self._deployed_capital)

    def place_simulated_order(self, order: OrderRequest, now: datetime) -> OrderResult:
        quote = self.market_data.get_quote(order.symbol)
        if quote is None:
            return OrderResult(False, f"no quote available for {order.symbol}")

        fill_price = self.slippage.apply(order.side, quote.ltp)
        capital_required = fill_price * order.quantity
        if capital_required > self.get_available_margin():
            return OrderResult(False, "insufficient simulated margin at fill time")

        trade = Trade(
            strategy=order.strategy,
            symbol=order.symbol,
            side=order.side.value,
            entry_time=now.isoformat(),
            entry_price=fill_price,
            qty=order.quantity,
            trade_date=now.date().isoformat(),
            initial_sl=order.initial_sl,
            trailing_sl=order.initial_sl,
            target=order.target,
            indicator_snapshot=order.indicator_snapshot,
            confidence_score=order.confidence_score,
            status="OPEN",
        )
        trade_id = self.db.insert_open_trade(trade)

        position = Position(
            trade_id=trade_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            entry_price=fill_price,
            initial_sl=order.initial_sl,
            trailing_sl=order.initial_sl,
            target=order.target,
            strategy=order.strategy,
            entry_time=now,
        )
        self._open_positions[trade_id] = position
        self._deployed_capital += capital_required
        return OrderResult(True, "filled", trade_id=trade_id, fill_price=fill_price)

    def get_open_positions(self) -> list[Position]:
        return list(self._open_positions.values())

    def update_trailing_stops(self, atr_by_symbol: dict[str, float]) -> None:
        for position in self._open_positions.values():
            atr = atr_by_symbol.get(position.symbol)
            if atr is None:
                continue
            quote = self.market_data.get_quote(position.symbol)
            if quote is None:
                continue
            new_sl = self.stop_target_calc.update_trailing_stop(position.side, quote.ltp, position.trailing_sl, atr)
            if new_sl != position.trailing_sl:
                position.trailing_sl = new_sl
                self.db.update_trailing_sl(position.trade_id, new_sl)

    def check_exits(self, now: datetime) -> list[OrderResult]:
        results: list[OrderResult] = []
        for trade_id in list(self._open_positions):
            position = self._open_positions[trade_id]
            quote = self.market_data.get_quote(position.symbol)
            if quote is None:
                continue

            exit_reason = self._exit_reason(position, quote.ltp)
            if exit_reason:
                results.append(self._close_position(position, quote.ltp, exit_reason, now))
        return results

    @staticmethod
    def _exit_reason(position: Position, ltp: float) -> str | None:
        sl_moved = position.trailing_sl != position.initial_sl
        if position.side == Signal.BUY:
            if ltp <= position.trailing_sl:
                return "TRAILING_SL" if sl_moved else "SL_HIT"
            if ltp >= position.target:
                return "TARGET_HIT"
        else:
            if ltp >= position.trailing_sl:
                return "TRAILING_SL" if sl_moved else "SL_HIT"
            if ltp <= position.target:
                return "TARGET_HIT"
        return None

    def flatten_all(self, reason: str, now: datetime) -> list[OrderResult]:
        results: list[OrderResult] = []
        for trade_id in list(self._open_positions):
            position = self._open_positions[trade_id]
            quote = self.market_data.get_quote(position.symbol)
            reference_price = quote.ltp if quote else position.entry_price
            results.append(self._close_position(position, reference_price, reason, now))
        return results

    def _close_position(self, position: Position, reference_price: float, reason: str, now: datetime) -> OrderResult:
        closing_side = Signal.SELL if position.side == Signal.BUY else Signal.BUY
        fill_price = self.slippage.apply(closing_side, reference_price)

        if position.side == Signal.BUY:
            pnl = (fill_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - fill_price) * position.quantity

        holding_seconds = int((now - position.entry_time).total_seconds())
        self.db.close_trade(position.trade_id, now.isoformat(), fill_price, reason, pnl, holding_seconds)

        if self.csv_path:
            trade = Trade(
                id=position.trade_id,
                strategy=position.strategy,
                symbol=position.symbol,
                side=position.side.value,
                entry_time=position.entry_time.isoformat(),
                entry_price=position.entry_price,
                qty=position.quantity,
                trade_date=position.entry_time.date().isoformat(),
                initial_sl=position.initial_sl,
                trailing_sl=position.trailing_sl,
                target=position.target,
                exit_time=now.isoformat(),
                exit_price=fill_price,
                exit_reason=reason,
                pnl=pnl,
                holding_seconds=holding_seconds,
                status="CLOSED",
            )
            csv_export.append_closed_trade(trade, self.csv_path)

        self._deployed_capital -= position.entry_price * position.quantity
        del self._open_positions[position.trade_id]
        return OrderResult(True, reason, trade_id=position.trade_id, fill_price=fill_price, pnl=pnl)
