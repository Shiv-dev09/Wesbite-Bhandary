"""Session VWAP -- Kite doesn't expose VWAP directly, so it's computed here
from the session's intraday bars as cumulative(typical_price * volume) /
cumulative(volume)."""
from __future__ import annotations

from datetime import datetime

from indicators.types import Bar


def session_bars_only(bars: list[Bar], current_time: datetime) -> list[Bar]:
    """Slices trailing bars down to just the current calendar day, so VWAP
    (and any other session-scoped indicator) resets at each new session
    instead of blending across days. Assumes `bars` is sorted oldest-first."""
    current_date = current_time.date()
    start = len(bars)
    for i in range(len(bars) - 1, -1, -1):
        if bars[i].timestamp.date() != current_date:
            break
        start = i
    return bars[start:]


def session_vwap(bars: list[Bar]) -> float | None:
    """VWAP across all given bars, treated as one session. Callers are
    responsible for passing only bars from the current trading session
    (i.e. slice from the day's open bar onward)."""
    if not bars:
        return None
    cum_pv = 0.0
    cum_vol = 0
    for bar in bars:
        typical_price = (bar.high + bar.low + bar.close) / 3.0
        cum_pv += typical_price * bar.volume
        cum_vol += bar.volume
    if cum_vol == 0:
        return None
    return cum_pv / cum_vol


def session_vwap_series(bars: list[Bar]) -> list[float | None]:
    """Running VWAP value after each bar, same length as `bars`."""
    out: list[float | None] = [None] * len(bars)
    cum_pv = 0.0
    cum_vol = 0
    for i, bar in enumerate(bars):
        typical_price = (bar.high + bar.low + bar.close) / 3.0
        cum_pv += typical_price * bar.volume
        cum_vol += bar.volume
        out[i] = (cum_pv / cum_vol) if cum_vol > 0 else None
    return out
