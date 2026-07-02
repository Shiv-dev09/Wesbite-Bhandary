"""Central Pivot Range (CPR) computed from the previous day's H/L/C."""
from __future__ import annotations

from dataclasses import dataclass

from indicators.types import Bar


@dataclass(frozen=True)
class CPR:
    pivot: float
    bc: float  # bottom central
    tc: float  # top central

    @property
    def width_pct(self) -> float:
        if self.pivot == 0:
            return 0.0
        return abs(self.tc - self.bc) / self.pivot * 100.0

    @property
    def is_narrow(self) -> bool:
        """Narrow CPR (relative to typical ~0.5% width) often precedes a
        trending breakout day. Threshold is caller-configurable via
        width_pct comparison; this property uses a common 0.5% heuristic."""
        return self.width_pct < 0.5


def central_pivot_range(prev_day_bar: Bar) -> CPR:
    pivot = (prev_day_bar.high + prev_day_bar.low + prev_day_bar.close) / 3.0
    bc = (prev_day_bar.high + prev_day_bar.low) / 2.0
    tc = (pivot - bc) + pivot
    lo, hi = sorted((bc, tc))
    return CPR(pivot=pivot, bc=lo, tc=hi)
