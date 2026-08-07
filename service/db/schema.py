from sqlite3 import Connection

_QUOTAS_DDL = """
CREATE TABLE IF NOT EXISTS quotas (
    org_id        TEXT    NOT NULL,
    feature       TEXT    NOT NULL,
    quota_limit   INTEGER NOT NULL,
    anchor_day    INTEGER NOT NULL,
    period_start  TEXT    NOT NULL,
    used          INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (org_id, feature)
);
"""

_IDEMPOTENCY_KEYS_DDL = """
CREATE TABLE IF NOT EXISTS idempotency_keys (
    request_id      TEXT    PRIMARY KEY,
    org_id          TEXT    NOT NULL,
    feature         TEXT    NOT NULL,
    payload_hash    TEXT    NOT NULL,
    units_deducted  INTEGER NOT NULL,
    units_refunded  INTEGER NOT NULL DEFAULT 0,
    response_body   TEXT,
    created_at      INTEGER NOT NULL
);
"""

_IDEMPOTENCY_CREATED_AT_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_idempotency_created_at
    ON idempotency_keys(created_at);
"""


def init_schema(conn: Connection) -> None:
    conn.execute(_QUOTAS_DDL)
    conn.execute(_IDEMPOTENCY_KEYS_DDL)
    conn.execute(_IDEMPOTENCY_CREATED_AT_INDEX_DDL)
    conn.commit()
