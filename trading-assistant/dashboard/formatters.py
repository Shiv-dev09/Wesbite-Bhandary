"""Small formatting helpers for the terminal dashboard."""
from __future__ import annotations


def format_currency(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}₹{abs(value):,.2f}"


def format_pct(value: float) -> str:
    return f"{value:.1f}%"


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "-"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
