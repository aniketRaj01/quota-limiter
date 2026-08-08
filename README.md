# Quota Limiter

Per-customer quota metering: tracks and enforces monthly, per-organization, per-feature
usage quotas with atomic concurrent-safe deduction, idempotent retries, and compensating
refunds on downstream failure. Built as a Portcast take-home assignment.

See [DESIGN.md](DESIGN.md) for the design decisions and their rationale.

## Quickstart

```bash
./setup.sh && ./run.sh
```

Then open `http://localhost:8000/docs` for interactive Swagger docs. Seed data (see
below) means you can start exercising the API immediately — no manual org creation
required.

## What's implemented

- `POST /v1/orgs` — create an org with per-feature quota limits. Server-generates the
  `orgId`, derives the reset anchor from the creation timestamp.
- `GET /v1/orgs` — list orgs and their next reset time.
- `GET /v1/quota/usage` — read-only usage reporting for a given org + feature.
- `POST /v1/features/container-tracking/track` — the quota component's live consumer.
  Wires together idempotency dedup, atomic all-or-nothing deduction, simulated
  per-container downstream failure, and compensating refunds.
- `GET /health` — liveness check.

Quota deduction, lazy monthly rollover, request-idempotency dedup, and refund are all
implemented as atomic conditional SQL updates (`UPDATE ... WHERE ... RETURNING`) — never
a read-then-write — so concurrent requests against the same org/feature can't over-serve.

## Seed data

Three orgs exist on boot, all with a `container-tracking` quota:

| orgId | limit |
|---|---|
| `org_demo` | 20 |
| `org_demo_low` | 10 |
| `org_demo_concurrency` | 50 |

## API examples

Create an org:

```bash
curl -s -X POST http://localhost:8000/v1/orgs \
  -H 'Content-Type: application/json' \
  -d '{"quotas": [{"feature": "container-tracking", "limit": 500}]}'
```

Check usage:

```bash
curl -s "http://localhost:8000/v1/quota/usage?orgId=org_demo&feature=container-tracking"
```

Track containers — full success:

```bash
curl -s -X POST http://localhost:8000/v1/features/container-tracking/track \
  -H 'Content-Type: application/json' \
  -d '{"requestId": "req-1", "orgId": "org_demo", "containerIds": ["c1", "c2", "c3"]}'
```

Track containers — mixed success/failure (any containerId containing `"fail"` is
simulated as a downstream failure, deducted then refunded):

```bash
curl -s -X POST http://localhost:8000/v1/features/container-tracking/track \
  -H 'Content-Type: application/json' \
  -d '{"requestId": "req-2", "orgId": "org_demo", "containerIds": ["c1", "c-fail-1"]}'
```

Insufficient quota (429) — `org_demo_low` only has 10 headroom:

```bash
curl -s -X POST http://localhost:8000/v1/features/container-tracking/track \
  -H 'Content-Type: application/json' \
  -d '{"requestId": "req-3", "orgId": "org_demo_low", "containerIds": ["c1","c2","c3","c4","c5","c6","c7","c8","c9","c10","c11"]}'
```

Retry the same `requestId` + payload — returns the cached response, no double-deduct.
Retry with a different payload under the same `requestId` — `409` conflict.

## Running the tests

```bash
source venv/bin/activate
pytest -q
```

Tests are organized by what they prove:

- `tests/unit/` — direct function calls against each service (quota, idempotency,
  refund, track, period-boundary math), no HTTP.
- `tests/integration/` — full HTTP round trips via `TestClient` (org creation, `/track`,
  `/quota/usage`).
- `tests/concurrency/` — the heavily-weighted correctness-under-contention tests: real
  `ThreadPoolExecutor` threads racing against a nearly-exhausted quota, asserting the
  actual bar (`used` never exceeds `limit`, no negative remaining, exact final count),
  proven both against the core primitive directly and through the full `/track` stack.
- `tests/performance/` — a latency regression test asserting the core quota operation
  stays under the assignment's 10ms budget.

## Running the load test

The load generator is the "consumer running under load" deliverable made reproducible.
It fires real concurrent HTTP requests (not `TestClient`) at a live server and reports
p50/p95/p99 latency and throughput.

```bash
# terminal 1
./run.sh

# terminal 2
source venv/bin/activate
python load_test/load_test.py --base-url http://localhost:8000 --concurrency 50 --requests 2000
```

Flags: `--concurrency`, `--requests`, `--base-url`, `--output` (default
`load_test/results.txt`, gitignored — it's a reproducible run artifact, not committed).

## Project structure

```
service/
  routes/       APIRouters — HTTP method/path/response_model only, no logic
  controllers/  request/response shaping, maps service results onto schemas
  services/     business logic — quota math, idempotency, refund, track orchestration
  repos/        persistence — every SQL statement lives here
  schemas/      Pydantic request/response models
  db/           single long-lived sqlite3 :memory: connection + schema + seed data
tests/          unit / integration / concurrency / performance, see above
load_test/      real load generator against a live server
```

## Scaling to 50,000 orgs

Not implemented — this build is a single-process design (see "What's implemented" above).
The target architecture (shared Redis for the atomic hot path, Postgres as the durable
system of record) is described and diagrammed in [DESIGN.md](DESIGN.md#scaling-to-50000-orgs-not-built),
and sketched at a higher level here:
[High-level architecture diagram](https://excalidraw.com/#json=OA2OVt-V07uMptAjaQRM0,U7xsKZ0m_Uj1uo3fp-bXZQ).
