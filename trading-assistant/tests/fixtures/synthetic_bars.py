"""Synthetic OHLCV bar generators for tests -- no live/historical Kite
data required. Bars are 1-minute, starting at 09:15 IST on the given date."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from indicators.types import Bar
from utils.time_utils import IST


def _start_time(day_offset: int = 0) -> datetime:
    base = datetime(2026, 6, 1, 9, 15, tzinfo=IST) + timedelta(days=day_offset)
    return base


def make_bars(
    count: int,
    start_price: float = 100.0,
    step: float = 0.0,
    volume: int = 10_000,
    day_offset: int = 0,
    noise: float = 0.0,
    seed: int = 42,
) -> list[Bar]:
    """A simple deterministic trending/flat series: close moves by `step`
    each bar, with optional uniform noise. High/low bracket open/close by
    a small fixed amount so ATR/candle checks have something to chew on."""
    rng = random.Random(seed)
    bars: list[Bar] = []
    price = start_price
    ts = _start_time(day_offset)
    for i in range(count):
        open_ = price
        drift = step + (rng.uniform(-noise, noise) if noise else 0.0)
        close = max(0.01, open_ + drift)
        high = max(open_, close) + abs(drift) * 0.5 + 0.05
        low = min(open_, close) - abs(drift) * 0.5 - 0.05
        bars.append(Bar(timestamp=ts, open=open_, high=high, low=low, close=close, volume=volume))
        price = close
        ts = ts + timedelta(minutes=1)
    return bars


def make_trending_bars(count: int, start_price: float = 100.0, up: bool = True, day_offset: int = 0) -> list[Bar]:
    step = 0.15 if up else -0.15
    return make_bars(count, start_price=start_price, step=step, day_offset=day_offset, noise=0.02)


def make_choppy_bars(count: int, start_price: float = 100.0, day_offset: int = 0) -> list[Bar]:
    return make_bars(count, start_price=start_price, step=0.0, day_offset=day_offset, noise=0.1)


def make_breakout_bars(
    pre_count: int, start_price: float = 100.0, breakout_pct: float = 1.0, day_offset: int = 0
) -> list[Bar]:
    """Flat/tight opening range for `pre_count` bars, followed by a sharp
    breakout bar with a volume surge -- useful for ORB/volume-breakout
    strategy tests."""
    flat = make_bars(pre_count, start_price=start_price, step=0.0, volume=5_000, day_offset=day_offset, noise=0.01)
    last_close = flat[-1].close
    breakout_price = last_close * (1 + breakout_pct / 100.0)
    ts = flat[-1].timestamp + timedelta(minutes=1)
    breakout_bar = Bar(
        timestamp=ts,
        open=last_close,
        high=breakout_price + 0.1,
        low=last_close - 0.05,
        close=breakout_price,
        volume=50_000,
    )
    return flat + [breakout_bar]


def make_gap_up_bars(count: int, start_price: float = 100.0, gap_pct: float = 2.0, day_offset: int = 0) -> list[Bar]:
    pre = make_bars(count // 2, start_price=start_price, step=0.0, day_offset=day_offset, noise=0.02)
    gapped_start = pre[-1].close * (1 + gap_pct / 100.0)
    post = make_bars(
        count - len(pre), start_price=gapped_start, step=0.05, day_offset=day_offset, noise=0.02, seed=99
    )
    ts = pre[-1].timestamp + timedelta(minutes=1)
    adjusted_post = []
    for i, b in enumerate(post):
        adjusted_post.append(
            Bar(timestamp=ts + timedelta(minutes=i), open=b.open, high=b.high, low=b.low, close=b.close, volume=b.volume)
        )
    return pre + adjusted_post
