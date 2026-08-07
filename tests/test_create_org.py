import re
from datetime import datetime, timezone

import pytest

from service.services import org_service
from service.services.period import next_reset_at

ORG_ID_PATTERN = re.compile(r"^org_[0-9a-f]{8}$")


def test_create_org_succeeds_with_expected_shape(client):
    response = client.post(
        "/v1/orgs",
        json={"quotas": [{"feature": "container-tracking", "limit": 30}]},
    )

    assert response.status_code == 201
    body = response.json()

    assert ORG_ID_PATTERN.match(body["orgId"])
    assert 1 <= body["anchorDay"] <= 31
    assert body["quotas"] == [
        {
            "feature": "container-tracking",
            "limit": 30,
            "used": 0,
            "periodStart": body["quotas"][0]["periodStart"],
            "resetsAt": body["quotas"][0]["resetsAt"],
        }
    ]


def test_create_org_computes_period_start_and_resets_at(client):
    response = client.post(
        "/v1/orgs",
        json={"quotas": [{"feature": "container-tracking", "limit": 10}]},
    )
    body = response.json()
    quota = body["quotas"][0]

    now = datetime.now(timezone.utc).date()

    assert quota["periodStart"] == now.isoformat()
    assert body["anchorDay"] == now.day
    assert quota["resetsAt"] == next_reset_at(now, body["anchorDay"])


def test_create_org_inserts_one_quota_row_per_feature(client):
    response = client.post(
        "/v1/orgs",
        json={
            "quotas": [
                {"feature": "container-tracking", "limit": 30},
                {"feature": "other-feature", "limit": 15},
            ]
        },
    )

    body = response.json()
    limits_by_feature = {q["feature"]: q["limit"] for q in body["quotas"]}
    assert limits_by_feature == {"container-tracking": 30, "other-feature": 15}


def test_created_org_appears_in_list(client):
    create_response = client.post(
        "/v1/orgs",
        json={"quotas": [{"feature": "container-tracking", "limit": 30}]},
    )
    org_id = create_response.json()["orgId"]

    list_response = client.get("/v1/orgs")
    org_ids = [org["orgId"] for org in list_response.json()]

    assert org_id in org_ids


def test_duplicate_org_id_raises(client, monkeypatch):
    class FixedUUID:
        hex = "11111111111111111111111111111111"

    monkeypatch.setattr(org_service.uuid, "uuid4", lambda: FixedUUID())

    org_service.create_org([("container-tracking", 10)])

    with pytest.raises(org_service.DuplicateOrgError):
        org_service.create_org([("container-tracking", 10)])
