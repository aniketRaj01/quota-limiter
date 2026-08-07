"""
Load test for POST /v1/features/container-tracking/track.

Fires real concurrent HTTP requests (asyncio + httpx) at an already-running server,
measuring per-request latency (p50/p95/p99) and sustained throughput. Creates its own
org up front with enough headroom that every request succeeds, so the numbers reflect
the full success path (idempotency check + atomic deduct + simulated downstream +
response caching), not rejection short-circuits.

Usage:
    ./run.sh &                     # start the server first
    python scripts/load_test.py [--base-url http://localhost:8000]
                                 [--concurrency 50] [--requests 2000]
                                 [--output scripts/load_test_results.txt]
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx


@dataclass
class RequestResult:
    latency_ms: float
    status_code: int


async def _create_org(client: httpx.AsyncClient, limit: int) -> str:
    response = await client.post(
        "/v1/orgs", json={"quotas": [{"feature": "container-tracking", "limit": limit}]}
    )
    response.raise_for_status()
    return response.json()["orgId"]


async def _fire_one(client: httpx.AsyncClient, org_id: str) -> RequestResult:
    payload = {
        "requestId": str(uuid.uuid4()),
        "orgId": org_id,
        "containerIds": ["c1", "c2", "c3"],
    }
    start = time.perf_counter()
    response = await client.post("/v1/features/container-tracking/track", json=payload)
    latency_ms = (time.perf_counter() - start) * 1000
    return RequestResult(latency_ms=latency_ms, status_code=response.status_code)


async def run(base_url: str, concurrency: int, total_requests: int) -> tuple[list[RequestResult], float]:
    limits = httpx.Limits(max_connections=concurrency + 10, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0, limits=limits) as client:
        org_id = await _create_org(client, limit=total_requests * 3 + 1000)

        semaphore = asyncio.Semaphore(concurrency)

        async def worker() -> RequestResult:
            async with semaphore:
                return await _fire_one(client, org_id)

        start = time.perf_counter()
        results = list(await asyncio.gather(*(worker() for _ in range(total_requests))))
        wall_clock_s = time.perf_counter() - start

    return results, wall_clock_s


def _percentile(sorted_values: list[float], p: float) -> float:
    idx = min(len(sorted_values) - 1, int(len(sorted_values) * p))
    return sorted_values[idx]


def summarize(results: list[RequestResult], wall_clock_s: float, concurrency: int) -> str:
    latencies = sorted(r.latency_ms for r in results)
    statuses: dict[int, int] = {}
    for r in results:
        statuses[r.status_code] = statuses.get(r.status_code, 0) + 1

    lines = [
        f"timestamp:      {datetime.now(timezone.utc).isoformat()}",
        f"requests:       {len(results)}",
        f"concurrency:    {concurrency}",
        f"wall clock:     {wall_clock_s:.3f}s",
        f"throughput:     {len(results) / wall_clock_s:.1f} req/s",
        f"status codes:   {statuses}",
        f"latency p50:    {_percentile(latencies, 0.50):.3f}ms",
        f"latency p95:    {_percentile(latencies, 0.95):.3f}ms",
        f"latency p99:    {_percentile(latencies, 0.99):.3f}ms",
        f"latency min:    {latencies[0]:.3f}ms",
        f"latency max:    {latencies[-1]:.3f}ms",
        f"latency mean:   {statistics.mean(latencies):.3f}ms",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--requests", type=int, default=2000)
    parser.add_argument("--output", default="scripts/load_test_results.txt")
    args = parser.parse_args()

    results, wall_clock_s = asyncio.run(run(args.base_url, args.concurrency, args.requests))
    summary = summarize(results, wall_clock_s, args.concurrency)

    print(summary)

    with open(args.output, "w") as f:
        f.write(summary + "\n")


if __name__ == "__main__":
    main()
