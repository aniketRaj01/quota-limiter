from __future__ import annotations

from sqlite3 import Connection, Row


def insert_quota(
    conn: Connection,
    org_id: str,
    feature: str,
    quota_limit: int,
    anchor_day: int,
    period_start: str,
) -> None:
    conn.execute(
        """
        INSERT INTO quotas (org_id, feature, quota_limit, anchor_day, period_start, used)
        VALUES (:org_id, :feature, :quota_limit, :anchor_day, :period_start, 0)
        """,
        {
            "org_id": org_id,
            "feature": feature,
            "quota_limit": quota_limit,
            "anchor_day": anchor_day,
            "period_start": period_start,
        },
    )


def get_quota(conn: Connection, org_id: str, feature: str) -> Row | None:
    return conn.execute(
        """
        SELECT org_id, feature, quota_limit, anchor_day, period_start, used
        FROM quotas
        WHERE org_id = :org_id AND feature = :feature
        """,
        {"org_id": org_id, "feature": feature},
    ).fetchone()


def list_quotas_for_org(conn: Connection, org_id: str) -> list[Row]:
    return conn.execute(
        """
        SELECT org_id, feature, quota_limit, anchor_day, period_start, used
        FROM quotas
        WHERE org_id = :org_id
        """,
        {"org_id": org_id},
    ).fetchall()


def list_org_summaries(conn: Connection) -> list[Row]:
    return conn.execute(
        """
        SELECT org_id, MIN(anchor_day) AS anchor_day
        FROM quotas
        GROUP BY org_id
        """
    ).fetchall()


def org_exists(conn: Connection, org_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM quotas WHERE org_id = :org_id LIMIT 1",
        {"org_id": org_id},
    ).fetchone()
    return row is not None
