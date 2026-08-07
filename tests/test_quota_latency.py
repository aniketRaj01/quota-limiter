from __future__ import annotations

import statistics
import time

from service.services import org_service
from service.services.quota import ConsumeStatus, check_and_consume

FEATURE = "container-tracking"
WARMUP_ITERATIONS = 20
MEASURED_ITERATIONS = 500
MAX_AVG_MS = 10.0
MAX_P95_MS = 10.0


def test_check_and_consume_stays_under_10ms_per_call(client):
    org_id = org_service.create_org([(FEATURE, 1_000_000)])["org_id"]

    for _ in range(WARMUP_ITERATIONS):
        check_and_consume(org_id, FEATURE, 1)

    durations_ms = []
    for _ in range(MEASURED_ITERATIONS):
        start = time.perf_counter()
        result = check_and_consume(org_id, FEATURE, 1)
        durations_ms.append((time.perf_counter() - start) * 1000)
        assert result.status == ConsumeStatus.OK

    avg_ms = statistics.mean(durations_ms)
    p95_ms = statistics.quantiles(durations_ms, n=100)[94]

    print(f"\ncheck_and_consume latency over {MEASURED_ITERATIONS} calls: "
          f"avg={avg_ms:.4f}ms p95={p95_ms:.4f}ms max={max(durations_ms):.4f}ms")

    assert avg_ms < MAX_AVG_MS, f"average latency {avg_ms:.4f}ms exceeds {MAX_AVG_MS}ms budget"
    assert p95_ms < MAX_P95_MS, f"p95 latency {p95_ms:.4f}ms exceeds {MAX_P95_MS}ms budget"
