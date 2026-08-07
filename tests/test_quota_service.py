from __future__ import annotations

from datetime import date, timedelta

from service.services import org_service
from service.services.quota import ConsumeStatus, check_and_consume

FEATURE = "container-tracking"


def _create_org(limit: int) -> str:
    return org_service.create_org([(FEATURE, limit)])["org_id"]


def test_normal_deduct_within_limit(client):
    org_id = _create_org(100)

    result = check_and_consume(org_id, FEATURE, 10)

    assert result.status == ConsumeStatus.OK
    assert result.used == 10
    assert result.limit == 100


def test_sequential_deducts_accumulate(client):
    org_id = _create_org(100)

    check_and_consume(org_id, FEATURE, 10)
    result = check_and_consume(org_id, FEATURE, 15)

    assert result.status == ConsumeStatus.OK
    assert result.used == 25


def test_exact_exhaustion_succeeds_and_leaves_zero_remaining(client):
    org_id = _create_org(500)

    result = check_and_consume(org_id, FEATURE, 500)

    assert result.status == ConsumeStatus.OK
    assert result.used == 500
    assert result.limit - result.used == 0


def test_insufficient_quota_rejects_and_leaves_used_unchanged(client):
    org_id = _create_org(10)
    check_and_consume(org_id, FEATURE, 8)

    result = check_and_consume(org_id, FEATURE, 5)

    assert result.status == ConsumeStatus.INSUFFICIENT_QUOTA
    assert result.used == 8
    assert result.limit == 10

    follow_up = check_and_consume(org_id, FEATURE, 2)
    assert follow_up.status == ConsumeStatus.OK
    assert follow_up.used == 10


def test_insufficient_quota_when_already_exhausted(client):
    org_id = _create_org(5)
    check_and_consume(org_id, FEATURE, 5)

    result = check_and_consume(org_id, FEATURE, 1)

    assert result.status == ConsumeStatus.INSUFFICIENT_QUOTA
    assert result.used == 5


def test_org_not_found(client):
    result = check_and_consume("org_does_not_exist", FEATURE, 1)

    assert result.status == ConsumeStatus.NOT_FOUND


def test_feature_not_configured_for_org(client):
    org_id = _create_org(10)

    result = check_and_consume(org_id, "some-other-feature", 1)

    assert result.status == ConsumeStatus.NOT_FOUND


def test_stale_period_rolls_over_before_deducting(client):
    org_id = _create_org(50)
    check_and_consume(org_id, FEATURE, 20)

    next_month = date.today() + timedelta(days=32)
    result = check_and_consume(org_id, FEATURE, 5, now=next_month)

    assert result.status == ConsumeStatus.OK
    assert result.used == 5
    assert result.period_start != date.today()


def test_stale_period_rollover_does_not_compound_across_multiple_gaps(client):
    org_id = _create_org(50)
    check_and_consume(org_id, FEATURE, 20)

    far_future = date.today() + timedelta(days=95)
    result = check_and_consume(org_id, FEATURE, 5, now=far_future)

    assert result.status == ConsumeStatus.OK
    assert result.used == 5


def test_stale_period_with_request_larger_than_limit_after_rollover(client):
    org_id = _create_org(10)
    check_and_consume(org_id, FEATURE, 10)

    next_month = date.today() + timedelta(days=32)
    result = check_and_consume(org_id, FEATURE, 20, now=next_month)

    assert result.status == ConsumeStatus.INSUFFICIENT_QUOTA
    assert result.used == 0
