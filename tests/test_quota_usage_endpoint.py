from __future__ import annotations

from datetime import date, timedelta

from service.db.connection import get_connection
from service.repos import quota_repo
from service.services import org_service
from service.services.quota import check_and_consume, get_usage

FEATURE = "container-tracking"


def _create_org(limit: int) -> str:
    return org_service.create_org([(FEATURE, limit)])["org_id"]


def test_fresh_org_usage(client):
    org_id = _create_org(30)

    response = client.get("/v1/quota/usage", params={"orgId": org_id, "feature": FEATURE})

    assert response.status_code == 200
    body = response.json()
    assert body["orgId"] == org_id
    assert body["feature"] == FEATURE
    assert body["limit"] == 30
    assert body["used"] == 0
    assert body["remaining"] == 30


def test_usage_reflects_prior_consumption(client):
    org_id = _create_org(30)
    check_and_consume(org_id, FEATURE, 12)

    response = client.get("/v1/quota/usage", params={"orgId": org_id, "feature": FEATURE})

    body = response.json()
    assert body["used"] == 12
    assert body["remaining"] == 18


def test_usage_past_reset_boundary_reports_zero_without_persisting_rollover(client):
    org_id = _create_org(30)
    check_and_consume(org_id, FEATURE, 12)

    original_period_start = quota_repo.get_quota(get_connection(), org_id, FEATURE)["period_start"]
    future = date.fromisoformat(original_period_start) + timedelta(days=32)

    result = get_usage(org_id, FEATURE, now=future)

    assert result.used == 0

    row = quota_repo.get_quota(get_connection(), org_id, FEATURE)
    assert row["used"] == 12
    assert row["period_start"] == original_period_start


def test_usage_404_for_unknown_org(client):
    response = client.get("/v1/quota/usage", params={"orgId": "org_does_not_exist", "feature": FEATURE})

    assert response.status_code == 404


def test_usage_404_for_unconfigured_feature(client):
    org_id = _create_org(30)

    response = client.get("/v1/quota/usage", params={"orgId": org_id, "feature": "some-other-feature"})

    assert response.status_code == 404
