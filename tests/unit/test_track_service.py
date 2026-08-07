from __future__ import annotations

from service.db.connection import get_connection
from service.repos import quota_repo
from service.services import org_service
from service.services.track import TrackStatus, track_containers

FEATURE = "container-tracking"


def _create_org(limit: int) -> str:
    return org_service.create_org([(FEATURE, limit)])["org_id"]


def _current_used(org_id: str) -> int:
    return quota_repo.get_quota(get_connection(), org_id, FEATURE)["used"]


def test_full_success_all_containers_succeed(client):
    org_id = _create_org(20)

    result = track_containers("trk-1", org_id, ["c1", "c2", "c3"])

    assert result.status == TrackStatus.OK
    assert result.body["status"] == "ok"
    assert result.body["requested"] == 3
    assert result.body["succeeded_container_ids"] == ["c1", "c2", "c3"]
    assert result.body["failed_container_ids"] == []
    assert result.body["units_refunded"] == 0
    assert result.body["remaining"] == 17
    assert _current_used(org_id) == 3


def test_mixed_success_and_failure_refunds_only_failed_units(client):
    org_id = _create_org(20)

    result = track_containers("trk-2", org_id, ["c1", "c2", "c-fail-1"])

    assert result.status == TrackStatus.OK
    assert result.body["succeeded_container_ids"] == ["c1", "c2"]
    assert result.body["failed_container_ids"] == ["c-fail-1"]
    assert result.body["units_refunded"] == 1
    assert result.body["remaining"] == 18
    assert _current_used(org_id) == 2


def test_all_containers_fail_refunds_full_batch(client):
    org_id = _create_org(20)

    result = track_containers("trk-3", org_id, ["c-FAIL-1", "c-fail-2"])

    assert result.status == TrackStatus.OK
    assert result.body["succeeded_container_ids"] == []
    assert result.body["failed_container_ids"] == ["c-FAIL-1", "c-fail-2"]
    assert result.body["units_refunded"] == 2
    assert result.body["remaining"] == 20
    assert _current_used(org_id) == 0


def test_insufficient_quota_is_all_or_nothing_and_deducts_nothing(client):
    org_id = _create_org(5)

    result = track_containers("trk-4", org_id, ["c1", "c2", "c3", "c4", "c5", "c6"])

    assert result.status == TrackStatus.INSUFFICIENT_QUOTA
    assert result.body["requested"] == 6
    assert result.body["remaining"] == 5
    assert result.body["limit"] == 5
    assert _current_used(org_id) == 0


def test_insufficient_quota_does_not_create_idempotency_row_so_retry_can_reevaluate(client):
    org_id = _create_org(3)

    first = track_containers("trk-5", org_id, ["c1", "c2", "c3", "c4"])
    assert first.status == TrackStatus.INSUFFICIENT_QUOTA

    retry_after_no_change = track_containers("trk-5", org_id, ["c1", "c2", "c3", "c4"])
    assert retry_after_no_change.status == TrackStatus.INSUFFICIENT_QUOTA
    assert _current_used(org_id) == 0


def test_exact_retry_of_same_request_id_returns_cached_response_no_double_deduct(client):
    org_id = _create_org(20)

    first = track_containers("trk-6", org_id, ["c1", "c2", "c-fail-1"])
    retry = track_containers("trk-6", org_id, ["c1", "c2", "c-fail-1"])

    assert retry.status == TrackStatus.OK
    assert retry.body == first.body
    assert _current_used(org_id) == 2


def test_replayed_request_id_with_different_payload_is_conflict(client):
    org_id = _create_org(20)

    track_containers("trk-7", org_id, ["c1", "c2"])
    result = track_containers("trk-7", org_id, ["c1", "c2", "c3"])

    assert result.status == TrackStatus.CONFLICT
    assert result.body["reason"] == "requestId already used with a different payload"
    assert _current_used(org_id) == 2


def test_replayed_request_id_under_different_org_is_conflict(client):
    org_a = _create_org(20)
    org_b = _create_org(20)

    track_containers("trk-8", org_a, ["c1", "c2"])
    result = track_containers("trk-8", org_b, ["c1", "c2"])

    assert result.status == TrackStatus.CONFLICT
    assert result.body["reason"] == "requestId already used by a different org/feature"
    assert _current_used(org_b) == 0


def test_org_not_found(client):
    result = track_containers("trk-9", "org_does_not_exist", ["c1"])

    assert result.status == TrackStatus.NOT_FOUND
