from __future__ import annotations

from sqlite3 import Connection, Row


def get(conn: Connection, request_id: str) -> Row | None:
    return conn.execute(
        """
        SELECT request_id, org_id, feature, payload_hash, units_deducted, units_refunded,
               response_body, created_at
        FROM idempotency_keys
        WHERE request_id = :request_id
        """,
        {"request_id": request_id},
    ).fetchone()


def delete(conn: Connection, request_id: str) -> None:
    conn.execute(
        "DELETE FROM idempotency_keys WHERE request_id = :request_id",
        {"request_id": request_id},
    )


def insert(
    conn: Connection,
    request_id: str,
    org_id: str,
    feature: str,
    payload_hash: str,
    units_deducted: int,
    created_at: int,
) -> None:
    conn.execute(
        """
        INSERT INTO idempotency_keys
            (request_id, org_id, feature, payload_hash, units_deducted, units_refunded,
             response_body, created_at)
        VALUES
            (:request_id, :org_id, :feature, :payload_hash, :units_deducted, 0, NULL, :created_at)
        """,
        {
            "request_id": request_id,
            "org_id": org_id,
            "feature": feature,
            "payload_hash": payload_hash,
            "units_deducted": units_deducted,
            "created_at": created_at,
        },
    )


def set_response(conn: Connection, request_id: str, response_body: str) -> None:
    conn.execute(
        "UPDATE idempotency_keys SET response_body = :response_body WHERE request_id = :request_id",
        {"request_id": request_id, "response_body": response_body},
    )


def refund(conn: Connection, request_id: str, amount: int) -> int | None:
    row = conn.execute(
        """
        UPDATE idempotency_keys
        SET units_refunded = units_refunded + :amount
        WHERE request_id = :request_id AND units_refunded + :amount <= units_deducted
        RETURNING units_refunded
        """,
        {"request_id": request_id, "amount": amount},
    ).fetchone()
    return row["units_refunded"] if row else None
