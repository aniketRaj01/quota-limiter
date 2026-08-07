from datetime import datetime, timezone
from sqlite3 import Connection

from service.repos import quota_repo
from service.schemas.feature import Feature

_SEED_ORGS = [
    {"org_id": "org_demo", "limit": 20},
    {"org_id": "org_demo_low", "limit": 10},
    {"org_id": "org_demo_concurrency", "limit": 50},
]


def seed_data(conn: Connection) -> None:
    if quota_repo.list_org_summaries(conn):
        return

    now = datetime.now(timezone.utc)
    anchor_day = now.day
    period_start = now.date().isoformat()

    for org in _SEED_ORGS:
        quota_repo.insert_quota(
            conn,
            org_id=org["org_id"],
            feature=Feature.CONTAINER_TRACKING.value,
            quota_limit=org["limit"],
            anchor_day=anchor_day,
            period_start=period_start,
        )
    conn.commit()
