from __future__ import annotations

from tests.fixtures.synthetic_bars import make_bars
from indicators.volume_profile import average_volume, is_volume_surge, relative_volume


def test_average_volume_insufficient_history():
    bars = make_bars(5, volume=1000)
    assert average_volume(bars, 20) is None


def test_relative_volume_flags_surge():
    bars = make_bars(21, volume=1000)
    surged = bars[:-1] + [
        bars[-1].__class__(
            timestamp=bars[-1].timestamp, open=bars[-1].open, high=bars[-1].high, low=bars[-1].low,
            close=bars[-1].close, volume=5000,
        )
    ]
    rv = relative_volume(surged, lookback=20)
    assert rv is not None
    assert rv >= 4.5
    assert is_volume_surge(surged, lookback=20, surge_multiple=2.0)


def test_relative_volume_no_surge_on_flat_volume():
    bars = make_bars(25, volume=1000)
    assert not is_volume_surge(bars, lookback=20, surge_multiple=2.0)
