from __future__ import annotations


def _create_org(client, limit: int) -> str:
    response = client.post(
        "/v1/orgs",
        json={"quotas": [{"feature": "container-tracking", "limit": limit}]},
    )
    return response.json()["orgId"]


def _track(client, request_id: str, org_id: str, container_ids: list[str]):
    return client.post(
        "/v1/features/container-tracking/track",
        json={"requestId": request_id, "orgId": org_id, "containerIds": container_ids},
    )


def test_full_success(client):
    org_id = _create_org(client, 20)

    response = _track(client, "http-trk-1", org_id, ["c1", "c2", "c3"])

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["orgId"] == org_id
    assert body["feature"] == "container-tracking"
    assert body["requested"] == 3
    assert body["succeededContainerIds"] == ["c1", "c2", "c3"]
    assert body["failedContainerIds"] == []
    assert body["unitsRefunded"] == 0
    assert body["remaining"] == 17


def test_mixed_success_and_failure(client):
    org_id = _create_org(client, 20)

    response = _track(client, "http-trk-2", org_id, ["c1", "c-fail-1"])

    assert response.status_code == 200
    body = response.json()
    assert body["succeededContainerIds"] == ["c1"]
    assert body["failedContainerIds"] == ["c-fail-1"]
    assert body["unitsRefunded"] == 1
    assert body["remaining"] == 19


def test_insufficient_quota_returns_429(client):
    org_id = _create_org(client, 2)

    response = _track(client, "http-trk-3", org_id, ["c1", "c2", "c3"])

    assert response.status_code == 429
    body = response.json()
    assert body["status"] == "insufficient_quota"
    assert body["orgId"] == org_id
    assert body["requested"] == 3
    assert body["remaining"] == 2
    assert body["limit"] == 2
    assert "resetsAt" in body


def test_insufficient_quota_deducts_nothing(client):
    org_id = _create_org(client, 2)

    _track(client, "http-trk-3b", org_id, ["c1", "c2", "c3"])
    follow_up = _track(client, "http-trk-3c", org_id, ["c1", "c2"])

    assert follow_up.status_code == 200
    assert follow_up.json()["remaining"] == 0


def test_exact_retry_returns_cached_response_no_double_deduct(client):
    org_id = _create_org(client, 20)

    first = _track(client, "http-trk-4", org_id, ["c1", "c-fail-1"])
    retry = _track(client, "http-trk-4", org_id, ["c1", "c-fail-1"])

    assert retry.status_code == 200
    assert retry.json() == first.json()

    usage_probe = _track(client, "http-trk-4-probe", org_id, ["c2"])
    assert usage_probe.json()["remaining"] == 18


def test_replayed_request_id_different_payload_returns_409(client):
    org_id = _create_org(client, 20)

    _track(client, "http-trk-5", org_id, ["c1"])
    response = _track(client, "http-trk-5", org_id, ["c1", "c2"])

    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "conflict"
    assert body["requestId"] == "http-trk-5"
    assert body["reason"] == "requestId already used with a different payload"


def test_replayed_request_id_different_org_returns_409(client):
    org_a = _create_org(client, 20)
    org_b = _create_org(client, 20)

    _track(client, "http-trk-6", org_a, ["c1"])
    response = _track(client, "http-trk-6", org_b, ["c1"])

    assert response.status_code == 409
    assert response.json()["reason"] == "requestId already used by a different org/feature"


def test_unknown_org_returns_404(client):
    response = _track(client, "http-trk-7", "org_does_not_exist", ["c1"])

    assert response.status_code == 404
