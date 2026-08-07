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


def deduct(
    conn: Connection,
    org_id: str,
    feature: str,
    units: int,
    period_start: str,
) -> int | None:
    row = conn.execute(
        """
        UPDATE quotas
        SET used = used + :units
        WHERE org_id = :org_id AND feature = :feature
          AND period_start = :period_start
          AND used + :units <= quota_limit
        RETURNING used
        """,
        {
            "org_id": org_id,
            "feature": feature,
            "units": units,
            "period_start": period_start,
        },
    ).fetchone()
    return row["used"] if row else None


def rollover(
    conn: Connection,
    org_id: str,
    feature: str,
    old_period_start: str,
    new_period_start: str,
) -> None:
    conn.execute(
        """
        UPDATE quotas
        SET period_start = :new_period_start, used = 0
        WHERE org_id = :org_id AND feature = :feature AND period_start = :old_period_start
        """,
        {
            "org_id": org_id,
            "feature": feature,
            "old_period_start": old_period_start,
            "new_period_start": new_period_start,
        },
    )


def credit(conn: Connection, org_id: str, feature: str, amount: int) -> int | None:
    row = conn.execute(
        """
        UPDATE quotas
        SET used = used - :amount
        WHERE org_id = :org_id AND feature = :feature AND used - :amount >= 0
        RETURNING used
        """,
        {"org_id": org_id, "feature": feature, "amount": amount},
    ).fetchone()
    return row["used"] if row else None
