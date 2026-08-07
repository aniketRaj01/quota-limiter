from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from enum import Enum

from service.db.connection import get_connection, get_lock
from service.repos import idempotency_repo, quota_repo

TTL_MS = 60_000


class IdempotencyStatus(str, Enum):
    NEW = "new"
    CACHED = "cached"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class IdempotencyResult:
    status: IdempotencyStatus
    response_body: str | None = None
    reason: str | None = None


class RefundStatus(str, Enum):
    OK = "ok"
    CAPPED = "capped"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class RefundResult:
    status: RefundStatus
    units_refunded_total: int
    used: int | None


def payload_fingerprint(feature: str, units: int, container_ids: list[str]) -> str:
    payload = json.dumps(
        {"feature": feature, "units": units, "containerIds": container_ids},
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def check(
    request_id: str,
    org_id: str,
    feature: str,
    payload_hash: str,
    now_ms: int | None = None,
) -> IdempotencyResult:
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    conn = get_connection()

    with get_lock():
        row = idempotency_repo.get(conn, request_id)
        if row is not None and now_ms - row["created_at"] > TTL_MS:
            idempotency_repo.delete(conn, request_id)
            conn.commit()
            row = None

        if row is None:
            return IdempotencyResult(IdempotencyStatus.NEW)

        if row["org_id"] != org_id or row["feature"] != feature:
            return IdempotencyResult(IdempotencyStatus.CONFLICT, reason="org_feature_mismatch")

        if row["payload_hash"] != payload_hash:
            return IdempotencyResult(IdempotencyStatus.CONFLICT, reason="payload_mismatch")

        return IdempotencyResult(IdempotencyStatus.CACHED, response_body=row["response_body"])


def reserve(
    request_id: str,
    org_id: str,
    feature: str,
    payload_hash: str,
    units_deducted: int,
    now_ms: int | None = None,
) -> None:
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    conn = get_connection()

    with get_lock():
        idempotency_repo.insert(conn, request_id, org_id, feature, payload_hash, units_deducted, now_ms)
        conn.commit()


def complete(request_id: str, response_body: str) -> None:
    conn = get_connection()

    with get_lock():
        idempotency_repo.set_response(conn, request_id, response_body)
        conn.commit()


def refund(request_id: str, org_id: str, feature: str, amount: int) -> RefundResult:
    conn = get_connection()

    with get_lock():
        row = idempotency_repo.get(conn, request_id)
        if row is None:
            return RefundResult(RefundStatus.NOT_FOUND, units_refunded_total=0, used=None)

        units_refunded_total = idempotency_repo.refund(conn, request_id, amount)
        if units_refunded_total is None:
            conn.commit()
            return RefundResult(
                RefundStatus.CAPPED, units_refunded_total=row["units_refunded"], used=None
            )

        used = quota_repo.credit(conn, org_id, feature, amount)
        conn.commit()
        return RefundResult(RefundStatus.OK, units_refunded_total=units_refunded_total, used=used)
