from __future__ import annotations

from datetime import datetime

from broker.interface import OrderRequest
from broker.paper_broker import PaperBroker
from broker.slippage import SlippageModel
from risk.stop_target import StopTargetCalculator
from strategies.base import Signal
from tests.test_broker.test_paper_broker_fills import FakeMarketData
from utils.time_utils import IST


def _now():
    return datetime(2026, 6, 1, 15, 15, tzinfo=IST)


def _order(symbol="RELIANCE", qty=10):
    return OrderRequest(
        symbol=symbol, side=Signal.BUY, quantity=qty, strategy="test", initial_sl=98.0, target=110.0,
        confidence_score=0.8, indicator_snapshot={},
    )


def test_flatten_all_closes_every_open_position(memory_db):
    market_data = FakeMarketData(ltp=100.0)
    broker = PaperBroker(memory_db, market_data, SlippageModel(0), StopTargetCalculator(), 25_000.0, csv_path=None)
    broker.place_simulated_order(_order("RELIANCE", qty=5), _now())
    broker.place_simulated_order(_order("INFY", qty=5), _now())
    assert len(broker.get_open_positions()) == 2

    results = broker.flatten_all("EOD_FLATTEN", _now())
    assert len(results) == 2
    assert all(r.reason == "EOD_FLATTEN" for r in results)
    assert len(broker.get_open_positions()) == 0


def test_flatten_all_noop_when_no_positions(memory_db):
    market_data = FakeMarketData(ltp=100.0)
    broker = PaperBroker(memory_db, market_data, SlippageModel(0), StopTargetCalculator(), 25_000.0, csv_path=None)
    results = broker.flatten_all("EOD_FLATTEN", _now())
    assert results == []


def test_flatten_all_releases_deployed_capital(memory_db):
    market_data = FakeMarketData(ltp=100.0)
    broker = PaperBroker(memory_db, market_data, SlippageModel(0), StopTargetCalculator(), 25_000.0, csv_path=None)
    broker.place_simulated_order(_order(qty=10), _now())
    assert broker.get_available_margin() < 25_000.0
    broker.flatten_all("EOD_FLATTEN", _now())
    assert broker.get_available_margin() == 25_000.0
