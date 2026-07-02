"""Small guard helpers used before feeding bars/quotes into indicators or
strategies -- rejects malformed data rather than letting NaNs/Nones
propagate silently into a trading decision."""
from __future__ import annotations

import math

from indicators.types import Bar, Quote


def is_valid_bar(bar: Bar) -> bool:
    values = (bar.open, bar.high, bar.low, bar.close)
    if any(v is None or math.isnan(v) for v in values):
        return False
    if bar.high < bar.low:
        return False
    if bar.volume < 0:
        return False
    return True


def filter_valid_bars(bars: list[Bar]) -> list[Bar]:
    return [b for b in bars if is_valid_bar(b)]


def is_valid_quote(quote: Quote | None) -> bool:
    if quote is None:
        return False
    if quote.ltp is None or math.isnan(quote.ltp) or quote.ltp <= 0:
        return False
    return True
