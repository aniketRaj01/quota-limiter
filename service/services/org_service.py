from __future__ import annotations

import uuid
from datetime import datetime, timezone

from service.db.connection import get_connection, get_lock
from service.repos import quota_repo
from service.services.period import current_period_start, next_reset_at


class DuplicateOrgError(Exception):
    pass


def list_orgs() -> list[dict]:
    conn = get_connection()
    now = datetime.now(timezone.utc).date()

    with get_lock():
        summaries = quota_repo.list_org_summaries(conn)

    return [
        {
            "org_id": row["org_id"],
            "resets_at": next_reset_at(
                current_period_start(row["anchor_day"], now), row["anchor_day"]
            ),
        }
        for row in summaries
    ]


def create_org(quota_configs: list[tuple[str, int]]) -> dict:
    conn = get_connection()
    now = datetime.now(timezone.utc)
    anchor_day = now.day
    period_start = now.date()
    period_start_str = period_start.isoformat()
    org_id = f"org_{uuid.uuid4().hex[:8]}"

    with get_lock():
        if quota_repo.org_exists(conn, org_id):
            raise DuplicateOrgError(org_id)

        for feature, limit in quota_configs:
            quota_repo.insert_quota(
                conn,
                org_id=org_id,
                feature=feature,
                quota_limit=limit,
                anchor_day=anchor_day,
                period_start=period_start_str,
            )
        conn.commit()

    resets_at = next_reset_at(period_start, anchor_day)
    return {
        "org_id": org_id,
        "anchor_day": anchor_day,
        "quotas": [
            {
                "feature": feature,
                "limit": limit,
                "used": 0,
                "period_start": period_start_str,
                "resets_at": resets_at,
            }
            for feature, limit in quota_configs
        ],
    }
