from __future__ import annotations

from datetime import datetime, timezone

from service.db.connection import get_connection
from service.repos import quota_repo
from service.services.period import current_period_start, next_reset_at


def list_orgs() -> list[dict]:
    conn = get_connection()
    now = datetime.now(timezone.utc).date()

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
