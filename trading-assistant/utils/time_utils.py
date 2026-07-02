"""IST session-time helpers. All trading-session logic (scan start, first
trade, cutoff, square-off) is expressed and compared in IST regardless of
the host machine's local timezone."""
from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    return datetime.now(IST)


def parse_hhmm(value: str) -> time:
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


def to_ist(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def is_at_or_after(now: datetime, cutoff: str) -> bool:
    return to_ist(now).time() >= parse_hhmm(cutoff)


def is_before(now: datetime, cutoff: str) -> bool:
    return to_ist(now).time() < parse_hhmm(cutoff)


def is_within(now: datetime, start: str, end: str) -> bool:
    t = to_ist(now).time()
    return parse_hhmm(start) <= t <= parse_hhmm(end)


def trading_date(now: datetime) -> date:
    return to_ist(now).date()


def is_weekday(now: datetime) -> bool:
    return to_ist(now).weekday() < 5  # Mon-Fri; NSE holiday calendar not modeled here
