from __future__ import annotations

from service.db.connection import get_connection
from service.repos import quota_repo
from service.services import org_service
from service.services.idempotency import RefundStatus, payload_fingerprint, refund, reserve
from service.services.quota import check_and_consume

FEATURE = "container-tracking"


def _create_org(limit: int) -> str:
    return org_service.create_org([(FEATURE, limit)])["org_id"]


def _current_used(org_id: str) -> int:
    return quota_repo.get_quota(get_connection(), org_id, FEATURE)["used"]


def _deduct_and_reserve(org_id: str, request_id: str, units: int) -> None:
    fp = payload_fingerprint(FEATURE, units, [f"c{i}" for i in range(units)])
    check_and_consume(org_id, FEATURE, units)
    reserve(request_id, org_id, FEATURE, fp, units_deducted=units)


def test_partial_refund_credits_quota_back(client):
    org_id = _create_org(20)
    _deduct_and_reserve(org_id, "req-refund-1", 10)

    result = refund("req-refund-1", org_id, FEATURE, 4)

    assert result.status == RefundStatus.OK
    assert result.units_refunded_total == 4
    assert result.used == 6
    assert _current_used(org_id) == 6


def test_refund_capped_at_units_deducted(client):
    org_id = _create_org(20)
    _deduct_and_reserve(org_id, "req-refund-2", 10)

    result = refund("req-refund-2", org_id, FEATURE, 15)

    assert result.status == RefundStatus.CAPPED
    assert _current_used(org_id) == 10


def test_cannot_double_refund_beyond_cap(client):
    org_id = _create_org(20)
    _deduct_and_reserve(org_id, "req-refund-3", 10)

    first = refund("req-refund-3", org_id, FEATURE, 10)
    assert first.status == RefundStatus.OK
    assert first.used == 0

    second = refund("req-refund-3", org_id, FEATURE, 10)
    assert second.status == RefundStatus.CAPPED
    assert _current_used(org_id) == 0


def test_refund_unknown_request_id_is_not_found(client):
    org_id = _create_org(20)

    result = refund("does-not-exist", org_id, FEATURE, 1)

    assert result.status == RefundStatus.NOT_FOUND
