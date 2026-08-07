from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

from service.schemas.feature import Feature
from service.services import idempotency
from service.services.period import next_reset_at
from service.services.quota import ConsumeStatus, check_and_consume

_FAIL_MARKER = "fail"

_CONFLICT_REASONS = {
    "payload_mismatch": "requestId already used with a different payload",
    "org_feature_mismatch": "requestId already used by a different org/feature",
}


class TrackStatus(str, Enum):
    OK = "ok"
    INSUFFICIENT_QUOTA = "insufficient_quota"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class TrackResult:
    status: TrackStatus
    body: dict


def track_containers(request_id: str, org_id: str, container_ids: list[str]) -> TrackResult:
    feature = Feature.CONTAINER_TRACKING.value
    units = len(container_ids)
    fingerprint = idempotency.payload_fingerprint(feature, units, container_ids)

    idem = idempotency.check(request_id, org_id, feature, fingerprint)

    if idem.status == idempotency.IdempotencyStatus.CACHED:
        return TrackResult(TrackStatus.OK, json.loads(idem.response_body))

    if idem.status == idempotency.IdempotencyStatus.CONFLICT:
        return TrackResult(
            TrackStatus.CONFLICT,
            {
                "status": "conflict",
                "request_id": request_id,
                "reason": _CONFLICT_REASONS[idem.reason],
            },
        )

    consume = check_and_consume(org_id, feature, units)

    if consume.status == ConsumeStatus.NOT_FOUND:
        return TrackResult(TrackStatus.NOT_FOUND, {})

    if consume.status == ConsumeStatus.INSUFFICIENT_QUOTA:
        return TrackResult(
            TrackStatus.INSUFFICIENT_QUOTA,
            {
                "status": "insufficient_quota",
                "org_id": org_id,
                "feature": feature,
                "requested": units,
                "remaining": consume.limit - consume.used,
                "limit": consume.limit,
                "resets_at": next_reset_at(consume.period_start, consume.anchor_day),
            },
        )

    idempotency.reserve(request_id, org_id, feature, fingerprint, units_deducted=units)

    succeeded: list[str] = []
    failed: list[str] = []
    for container_id in container_ids:
        (failed if _FAIL_MARKER in container_id.lower() else succeeded).append(container_id)

    used = consume.used
    if failed:
        refund_result = idempotency.refund(request_id, org_id, feature, len(failed))
        used = refund_result.used

    body = {
        "status": "ok",
        "org_id": org_id,
        "feature": feature,
        "requested": units,
        "succeeded_container_ids": succeeded,
        "failed_container_ids": failed,
        "units_refunded": len(failed),
        "remaining": consume.limit - used,
    }

    idempotency.complete(request_id, json.dumps(body))

    return TrackResult(TrackStatus.OK, body)
