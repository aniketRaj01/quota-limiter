from __future__ import annotations

import calendar
from datetime import date, datetime, timezone


def current_period_start(anchor_day: int, now: date) -> date:
    day = min(anchor_day, calendar.monthrange(now.year, now.month)[1])
    candidate = date(now.year, now.month, day)
    if candidate <= now:
        return candidate

    year = now.year - 1 if now.month == 1 else now.year
    month = 12 if now.month == 1 else now.month - 1
    day = min(anchor_day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_reset_at(period_start: date, anchor_day: int) -> str:
    year = period_start.year + 1 if period_start.month == 12 else period_start.year
    month = 1 if period_start.month == 12 else period_start.month + 1
    day = min(anchor_day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
