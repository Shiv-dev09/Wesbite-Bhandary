from __future__ import annotations

from broker.slippage import SlippageModel
from strategies.base import Signal


def test_buy_fills_worse_than_reference():
    model = SlippageModel(slippage_bps=10.0)
    fill = model.apply(Signal.BUY, 100.0)
    assert fill > 100.0


def test_sell_fills_worse_than_reference():
    model = SlippageModel(slippage_bps=10.0)
    fill = model.apply(Signal.SELL, 100.0)
    assert fill < 100.0


def test_zero_slippage_returns_reference_price():
    model = SlippageModel(slippage_bps=0.0)
    assert model.apply(Signal.BUY, 100.0) == 100.0
    assert model.apply(Signal.SELL, 100.0) == 100.0
