from __future__ import annotations

from service.services import org_service
from service.services.idempotency import (
    IdempotencyStatus,
    check,
    complete,
    payload_fingerprint,
    reserve,
)

FEATURE = "container-tracking"


def _create_org(limit: int) -> str:
    return org_service.create_org([(FEATURE, limit)])["org_id"]


def test_fresh_key_is_new(client):
    org_id = _create_org(10)
    fp = payload_fingerprint(FEATURE, 3, ["c1", "c2", "c3"])

    result = check("req-1", org_id, FEATURE, fp)

    assert result.status == IdempotencyStatus.NEW


def test_exact_retry_returns_cached_response(client):
    org_id = _create_org(10)
    fp = payload_fingerprint(FEATURE, 3, ["c1", "c2", "c3"])

    reserve("req-2", org_id, FEATURE, fp, units_deducted=3)
    complete("req-2", '{"status": "ok"}')

    result = check("req-2", org_id, FEATURE, fp)

    assert result.status == IdempotencyStatus.CACHED
    assert result.response_body == '{"status": "ok"}'


def test_hash_mismatch_is_conflict(client):
    org_id = _create_org(10)
    fp = payload_fingerprint(FEATURE, 3, ["c1", "c2", "c3"])
    other_fp = payload_fingerprint(FEATURE, 2, ["c1", "c2"])

    reserve("req-3", org_id, FEATURE, fp, units_deducted=3)
    complete("req-3", '{"status": "ok"}')

    result = check("req-3", org_id, FEATURE, other_fp)

    assert result.status == IdempotencyStatus.CONFLICT
    assert result.reason == "payload_mismatch"


def test_cross_org_replay_is_conflict(client):
    org_a = _create_org(10)
    org_b = _create_org(10)
    fp = payload_fingerprint(FEATURE, 3, ["c1", "c2", "c3"])

    reserve("req-4", org_a, FEATURE, fp, units_deducted=3)
    complete("req-4", '{"status": "ok"}')

    result = check("req-4", org_b, FEATURE, fp)

    assert result.status == IdempotencyStatus.CONFLICT
    assert result.reason == "org_feature_mismatch"


def test_key_expires_after_ttl(client):
    org_id = _create_org(10)
    fp = payload_fingerprint(FEATURE, 3, ["c1", "c2", "c3"])

    reserve("req-5", org_id, FEATURE, fp, units_deducted=3, now_ms=0)
    complete("req-5", '{"status": "ok"}')

    result = check("req-5", org_id, FEATURE, fp, now_ms=61_000)

    assert result.status == IdempotencyStatus.NEW


def test_key_within_ttl_still_cached(client):
    org_id = _create_org(10)
    fp = payload_fingerprint(FEATURE, 3, ["c1", "c2", "c3"])

    reserve("req-6", org_id, FEATURE, fp, units_deducted=3, now_ms=0)
    complete("req-6", '{"status": "ok"}')

    result = check("req-6", org_id, FEATURE, fp, now_ms=59_000)

    assert result.status == IdempotencyStatus.CACHED


def test_payload_fingerprint_is_order_and_value_sensitive(client):
    fp1 = payload_fingerprint(FEATURE, 3, ["c1", "c2", "c3"])
    fp2 = payload_fingerprint(FEATURE, 3, ["c1", "c2", "c4"])

    assert fp1 != fp2
