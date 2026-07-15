# Changelog

## [2.0.0] - 2026-07-15

### Added — Analytics Pipeline

#### Backend

**Event Aggregation Model** (`app/models/event_aggregation.py`)
- New `event_aggregations` table with hourly pre-aggregated counts
- Stores `flag_id`, `hour`, `variation`, `count` per row
- Unique constraint on `(flag_id, hour, variation)` enables safe UPSERT
- Composite index on `(flag_id, hour)` for fast time-range queries

**Batch Ingestion API** (`POST /api/v1/analytics/events`)
- SDK-facing endpoint authenticated via API key
- Accepts up to 500 events per request
- Returns `202 Accepted` immediately — never blocks on DB writes
- Unknown flag keys silently dropped — SDK never errors on missing flags

**In-Memory Event Queue** (`app/core/event_queue.py`)
- `asyncio.Queue` based producer-consumer pipeline
- Ingestion route enqueues events; single worker drains and aggregates
- Decouples HTTP ingestion from DB writes — prevents concurrent write pile-ups
- Graceful shutdown: worker drains queue before process exits

**Background Worker** (`event_worker` in `app/core/event_queue.py`)
- Single async task running for the lifetime of the app
- UPSERT aggregation: increments existing hourly bucket or inserts new row
- Error isolation: DB failures log and continue — worker never crashes
- Started and stopped via FastAPI `lifespan` context manager

**Analytics Query API**
- `GET /api/v1/analytics/projects/{project_id}/flags/{flag_key}` — time-series
  - Query params: `from_time`, `to_time`, `granularity` (hour/day)
  - Returns array of `{ timestamp, variation, count }` buckets
  - Default range: last 7 days
- `GET /api/v1/analytics/projects/{project_id}/flags/{flag_key}/summary`
  - Returns total evaluations + per-variation breakdown with percentages
  - JWT authenticated — dashboard facing

**Health Endpoint Update**
- Added `event_queue_depth` to `GET /health` response
- Shows how many batches are pending in the worker queue

#### SDK (`flagbase-sdk` v0.2.0)

**EventBuffer** (`flagbase/event_buffer.py`)
- Thread-safe buffer accumulates evaluation events locally
- Auto-flush triggers: buffer hits 100 events OR 30 seconds elapses
- `threading.Timer` for periodic flush, `threading.Lock` for thread safety
- `close()` cancels timer and flushes remaining events

**Automatic Evaluation Tracking**
- `evaluate()` now automatically records an event to the buffer
- `is_enabled()` inherits tracking via `evaluate()`
- Only records events for flags that exist (skips `reason == "default"`)

**New Public Methods**
- `flush()` — manually flush buffered events before process exit
- `close()` — flushes buffer, cancels timer, closes HTTP connections

**atexit Handler**
- Registered on client init — flushes remaining events on process exit
- Safety net for apps that forget to call `close()`

**New HTTP Method** (`flush_events` in `flagbase/http_client.py`)
- `POST /api/v1/analytics/events` — sends buffered event batches
- Raises `FlagBaseConnectionError` on network failure (caught by EventBuffer)

### Changed

- `app/main.py` — added `lifespan` context manager for worker lifecycle
- `app/main.py` — version bumped to `2.0.0`
- `app/api/v1/analytics.py` — ingestion route now uses queue instead of BackgroundTasks
- `flagbase/__init__.py` — version bumped to `0.2.0`, exports `EventBuffer`

### Tests

- Backend: 66 → 82 passing (+16 new tests)
  - `tests/test_analytics.py` — 12 ingestion and query API tests
  - `tests/test_e2e_analytics.py` — 4 end-to-end pipeline tests
- SDK: 47 → 55 passing (+8 new tests)
  - `tests/test_event_buffer.py` — EventBuffer unit tests

---

## [1.0.0] - 2026-07-11

Initial release. See FLAGBASE_SPEC.md for full V1 scope.

- FastAPI backend with three-layer architecture (router → service → repository)
- JWT authentication for dashboard routes
- API key authentication for SDK routes
- Feature flag CRUD with rollout percentage and targeting rules
- MurmurHash3 consistent user bucketing
- Evaluation engine with include/exclude rules
- Background event recording on every evaluation
- Published Python SDK (`flagbase-sdk==0.1.0`) with TTL cache and thread-safe evaluator