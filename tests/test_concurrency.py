from __future__ import annotations

import random
import uuid
from concurrent.futures import ThreadPoolExecutor

from service.db.connection import get_connection
from service.repos import quota_repo
from service.services import org_service
from service.services.quota import ConsumeStatus, check_and_consume

FEATURE = "container-tracking"


def _create_org(limit: int) -> str:
    return org_service.create_org([(FEATURE, limit)])["org_id"]


def _current_used(org_id: str) -> int:
    return quota_repo.get_quota(get_connection(), org_id, FEATURE)["used"]


def test_concurrent_single_unit_requests_never_exceed_limit(client):
    limit = 50
    org_id = _create_org(limit)
    workers = 300

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(lambda _: check_and_consume(org_id, FEATURE, 1), range(workers)))

    successes = [r for r in results if r.status == ConsumeStatus.OK]
    rejections = [r for r in results if r.status == ConsumeStatus.INSUFFICIENT_QUOTA]

    assert len(successes) == limit
    assert len(rejections) == workers - limit

    for result in results:
        assert result.used <= result.limit
        assert result.limit - result.used >= 0

    assert _current_used(org_id) == limit


def test_concurrent_variable_batch_sizes_never_exceed_limit(client):
    limit = 100
    org_id = _create_org(limit)
    workers = 150
    batch_sizes = [random.randint(1, 5) for _ in range(workers)]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(
            executor.map(lambda units: check_and_consume(org_id, FEATURE, units), batch_sizes)
        )

    successful_units = sum(
        units
        for units, result in zip(batch_sizes, results)
        if result.status == ConsumeStatus.OK
    )

    for result in results:
        assert result.used <= limit
        assert result.limit - result.used >= 0

    assert successful_units <= limit
    assert _current_used(org_id) == successful_units


def test_concurrent_requests_across_two_orgs_do_not_cross_contaminate(client):
    org_a = _create_org(30)
    org_b = _create_org(30)
    workers = 100

    def consume(i: int):
        org_id = org_a if i % 2 == 0 else org_b
        return org_id, check_and_consume(org_id, FEATURE, 1)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(consume, range(workers)))

    successes_a = sum(1 for org_id, r in results if org_id == org_a and r.status == ConsumeStatus.OK)
    successes_b = sum(1 for org_id, r in results if org_id == org_b and r.status == ConsumeStatus.OK)

    assert successes_a == 30
    assert successes_b == 30
    assert _current_used(org_a) == 30
    assert _current_used(org_b) == 30


def test_concurrent_track_requests_through_full_http_stack_never_over_serve(client):
    limit = 50
    org_response = client.post("/v1/orgs", json={"quotas": [{"feature": FEATURE, "limit": limit}]})
    org_id = org_response.json()["orgId"]
    workers = 150

    def call(_i: int):
        request_id = str(uuid.uuid4())
        return client.post(
            "/v1/features/container-tracking/track",
            json={"requestId": request_id, "orgId": org_id, "containerIds": ["c1"]},
        )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        responses = list(executor.map(call, range(workers)))

    successes = [r for r in responses if r.status_code == 200]
    rejections = [r for r in responses if r.status_code == 429]

    assert len(successes) == limit
    assert len(rejections) == workers - limit

    usage = client.get("/v1/quota/usage", params={"orgId": org_id, "feature": FEATURE})
    assert usage.json()["used"] == limit
