from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum

from service.db.connection import get_connection, get_lock
from service.repos import quota_repo
from service.services.period import current_period_start


class ConsumeStatus(str, Enum):
    OK = "ok"
    INSUFFICIENT_QUOTA = "insufficient_quota"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class ConsumeResult:
    status: ConsumeStatus
    used: int
    limit: int
    anchor_day: int
    period_start: date


class UsageStatus(str, Enum):
    OK = "ok"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class UsageResult:
    status: UsageStatus
    used: int
    limit: int
    anchor_day: int
    period_start: date


def check_and_consume(
    org_id: str, feature: str, units: int, now: date | None = None
) -> ConsumeResult:
    conn = get_connection()
    now = now if now is not None else datetime.now(timezone.utc).date()

    with get_lock():
        row = quota_repo.get_quota(conn, org_id, feature)
        if row is None:
            return ConsumeResult(
                ConsumeStatus.NOT_FOUND, used=0, limit=0, anchor_day=0, period_start=now
            )

        period = current_period_start(row["anchor_day"], now)
        period_str = period.isoformat()
        is_stale = row["period_start"] != period_str

        used = quota_repo.deduct(conn, org_id, feature, units, period_start=period_str)

        if used is None and is_stale:
            quota_repo.rollover(
                conn,
                org_id,
                feature,
                old_period_start=row["period_start"],
                new_period_start=period_str,
            )
            used = quota_repo.deduct(conn, org_id, feature, units, period_start=period_str)

        conn.commit()

        if used is None:
            reported_used = 0 if is_stale else row["used"]
            return ConsumeResult(
                ConsumeStatus.INSUFFICIENT_QUOTA,
                used=reported_used,
                limit=row["quota_limit"],
                anchor_day=row["anchor_day"],
                period_start=period,
            )

        return ConsumeResult(
            ConsumeStatus.OK,
            used=used,
            limit=row["quota_limit"],
            anchor_day=row["anchor_day"],
            period_start=period,
        )


def get_usage(org_id: str, feature: str, now: date | None = None) -> UsageResult:
    conn = get_connection()
    now = now if now is not None else datetime.now(timezone.utc).date()

    with get_lock():
        row = quota_repo.get_quota(conn, org_id, feature)

    if row is None:
        return UsageResult(UsageStatus.NOT_FOUND, used=0, limit=0, anchor_day=0, period_start=now)

    period = current_period_start(row["anchor_day"], now)
    used = row["used"] if row["period_start"] == period.isoformat() else 0

    return UsageResult(
        UsageStatus.OK,
        used=used,
        limit=row["quota_limit"],
        anchor_day=row["anchor_day"],
        period_start=period,
    )
