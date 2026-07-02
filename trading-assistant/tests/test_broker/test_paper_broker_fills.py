from __future__ import annotations

from datetime import datetime

from broker.interface import OrderRequest
from broker.market_data import MarketDataProvider
from broker.paper_broker import PaperBroker
from broker.slippage import SlippageModel
from indicators.types import Bar, Quote
from risk.stop_target import StopTargetCalculator
from strategies.base import Signal
from utils.time_utils import IST


class FakeMarketData(MarketDataProvider):
    def __init__(self, ltp: float = 100.0) -> None:
        self.ltp = ltp

    def get_quote(self, symbol: str):
        return Quote(
            symbol=symbol, ltp=self.ltp, bid=self.ltp - 0.05, ask=self.ltp + 0.05,
            volume=100_000, open=self.ltp, high=self.ltp, low=self.ltp, prev_close=self.ltp,
        )

    def get_bars(self, symbol: str, lookback=None):
        return []


def _now():
    return datetime(2026, 6, 1, 10, 0, tzinfo=IST)


def _broker(memory_db, ltp=100.0, starting_capital=25_000.0):
    market_data = FakeMarketData(ltp)
    slippage = SlippageModel(slippage_bps=0.0)
    stop_target_calc = StopTargetCalculator()
    broker = PaperBroker(memory_db, market_data, slippage, stop_target_calc, starting_capital, csv_path=None)
    return broker, market_data


def _order(symbol="RELIANCE", side=Signal.BUY, qty=10, sl=98.0, target=104.0):
    return OrderRequest(
        symbol=symbol, side=side, quantity=qty, strategy="test", initial_sl=sl, target=target,
        confidence_score=0.8, indicator_snapshot={},
    )


def test_place_order_fills_and_deploys_capital(memory_db):
    broker, _ = _broker(memory_db)
    result = broker.place_simulated_order(_order(), _now())
    assert result.accepted
    assert result.fill_price == 100.0
    assert len(broker.get_open_positions()) == 1
    assert broker.get_available_margin() == 25_000.0 - 1000.0


def test_place_order_rejected_when_margin_insufficient(memory_db):
    broker, _ = _broker(memory_db, starting_capital=500.0)
    result = broker.place_simulated_order(_order(qty=10), _now())
    assert not result.accepted
    assert "margin" in result.reason


def test_place_order_rejected_when_no_quote(memory_db):
    market_data = FakeMarketData()

    class NoQuote(FakeMarketData):
        def get_quote(self, symbol: str):
            return None

    broker = PaperBroker(memory_db, NoQuote(), SlippageModel(0), StopTargetCalculator(), 25_000.0, csv_path=None)
    result = broker.place_simulated_order(_order(), _now())
    assert not result.accepted


def test_check_exits_closes_on_target_hit(memory_db):
    broker, market_data = _broker(memory_db, ltp=100.0)
    broker.place_simulated_order(_order(sl=98.0, target=104.0), _now())
    market_data.ltp = 105.0
    results = broker.check_exits(_now())
    assert len(results) == 1
    assert results[0].reason == "TARGET_HIT"
    assert results[0].pnl == (105.0 - 100.0) * 10
    assert len(broker.get_open_positions()) == 0


def test_check_exits_closes_on_sl_hit(memory_db):
    broker, market_data = _broker(memory_db, ltp=100.0)
    broker.place_simulated_order(_order(sl=98.0, target=104.0), _now())
    market_data.ltp = 97.0
    results = broker.check_exits(_now())
    assert len(results) == 1
    assert results[0].reason == "SL_HIT"
    assert results[0].pnl < 0


def test_restore_open_positions_from_db_rows(memory_db):
    broker, _ = _broker(memory_db)
    broker.place_simulated_order(_order(), _now())
    rows = memory_db.get_open_trades()

    fresh_broker, _ = _broker(memory_db)
    fresh_broker.restore_open_positions(rows)
    assert len(fresh_broker.get_open_positions()) == 1
    assert fresh_broker.get_available_margin() == 25_000.0 - 1000.0
