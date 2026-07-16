# FlagBase

A self-hostable feature flag platform with a built-in analytics pipeline.

**Backend:** FastAPI · SQLAlchemy · PostgreSQL · Docker  
**SDK:** [flagbase-python-sdk](https://github.com/avdheshMANDLOI/flagbase-python-sdk) · Published on PyPI  
**Tests:** 82 passing (backend) · 55 passing (SDK)

---

## What it does

FlagBase lets you control feature rollouts without redeploying your application. You create flags in the platform, evaluate them from your application via the SDK, and roll features out gradually or based on targeting rules.

```python
from flagbase import FlagClient

client = FlagClient(api_key="proj_sk_...", host="http://localhost:8000")

if client.is_enabled("new-checkout", user_id="user_123"):
    show_new_checkout()
else:
    show_old_checkout()
```

Every evaluation is automatically tracked. Analytics data is aggregated and queryable via API — no extra code needed.

---

## Features

### Feature Flags
- Create and manage flags per project
- Enable/disable flags instantly without redeploying
- Gradual rollout by percentage (e.g. roll out to 10% of users first)
- Targeting rules — include or exclude users by email, country, or custom attributes
- Consistent user bucketing using MurmurHash3 — same user always gets the same result

### Authentication
- JWT-based auth for dashboard routes
- API key auth for SDK-facing routes
- SHA-256 key hashing — keys are never stored in plaintext

### Analytics Pipeline
- SDK buffers evaluation events locally and flushes in batches
- Backend accepts batches asynchronously — returns 202 immediately, never blocks evaluation
- Producer-consumer queue decouples ingestion from DB writes
- Events pre-aggregated into hourly buckets in Postgres
- Query API returns time-series and summary data per flag

### Python SDK
- TTL cache — avoids redundant HTTP calls for the same flag
- Thread-safe evaluation and event buffering
- Auto-flush every 30 seconds or every 100 events
- atexit handler — flushes remaining events on process exit
- Works as a context manager

---

## How the Analytics Pipeline Works

## System Architecture

![FlagBase System Architecture](docs/architecture.png)

```
SDK evaluates a flag
 │
 │  EventBuffer accumulates events locally
 │  Flushes every 30s or every 100 events
 │
 ▼
POST /api/v1/analytics/events   ← returns 202 immediately
 │
 ▼
asyncio.Queue  (producer-consumer buffer)
 │
 ▼
Background worker drains queue and UPSERTs into Postgres
 │
 ▼
event_aggregations table  (pre-aggregated hourly counts)
 │
 ▼
GET /api/v1/analytics/projects/{id}/flags/{key}          ← time-series
GET /api/v1/analytics/projects/{id}/flags/{key}/summary  ← variation breakdown
```

**Why this design:**
- 202 Accepted means the evaluation path is never slowed by analytics writes
- Pre-aggregated hourly buckets mean queries are fast regardless of traffic volume
- A single background worker serializes DB writes and prevents lock contention
- Graceful shutdown drains the queue before the process exits

---

## API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register a new user |
| POST | `/api/v1/auth/login` | Login, returns JWT |
| GET | `/api/v1/auth/me` | Get current user profile |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/projects` | List your projects |
| POST | `/api/v1/projects` | Create a project |
| GET | `/api/v1/projects/{id}` | Get a project |
| PATCH | `/api/v1/projects/{id}` | Update a project |
| DELETE | `/api/v1/projects/{id}` | Delete a project |

### Flags
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/projects/{id}/flags` | List flags |
| POST | `/api/v1/projects/{id}/flags` | Create a flag |
| PATCH | `/api/v1/projects/{id}/flags/{flag_id}` | Update a flag |
| DELETE | `/api/v1/projects/{id}/flags/{flag_id}` | Archive a flag |

### Rules
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/flags/{flag_id}/rules` | List targeting rules |
| POST | `/api/v1/flags/{flag_id}/rules` | Add a targeting rule |
| DELETE | `/api/v1/flags/{flag_id}/rules/{rule_id}` | Remove a rule |

### API Keys
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/projects/{id}/api-keys` | List API keys |
| POST | `/api/v1/projects/{id}/api-keys` | Generate an API key |
| DELETE | `/api/v1/projects/{id}/api-keys/{key_id}` | Revoke an API key |

### SDK Endpoints (API key auth)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/evaluate` | Evaluate a flag for a user |
| POST | `/api/v1/analytics/events` | Ingest batch evaluation events |

### Analytics (JWT auth)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/projects/{id}/flags/{key}` | Time-series evaluation counts |
| GET | `/api/v1/analytics/projects/{id}/flags/{key}/summary` | Variation breakdown with percentages |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check — DB status and event queue depth |

---

## Running Locally

**Prerequisites:** Docker Desktop

```bash
git clone https://github.com/avdheshMANDLOI/FlagBase.git
cd FlagBase
cp .env.example .env
docker compose up -d
```

API available at `http://localhost:8000`  
Swagger docs at `http://localhost:8000/docs`

---

## Running Tests

```bash
docker compose exec api python -m pytest /app/tests/ -v
```

---

## SDK

```bash
pip install flagbase-sdk
```

```python
from flagbase import FlagClient

client = FlagClient(
    api_key="proj_sk_...",
    host="http://localhost:8000",
    cache_ttl=30,         # cache flag results for 30 seconds
    flush_interval=30,    # flush analytics events every 30 seconds
    max_buffer_size=100,  # or flush immediately when 100 events accumulate
)

# Basic evaluation
enabled = client.is_enabled("dark-mode", user_id="user_123")

# With targeting context
enabled = client.is_enabled(
    "dark-mode",
    user_id="user_123",
    context={"email": "user@example.com", "country": "IN"},
)

# Flush and close on shutdown
client.close()
```

Full SDK documentation: [flagbase-python-sdk](https://github.com/avdheshMANDLOI/flagbase-python-sdk)

---

## Project Structure

```
app/
├── api/v1/          # Route handlers
├── core/            # Database, dependencies, security, event queue
├── models/          # SQLAlchemy models
├── repositories/    # DB access layer
├── schemas/         # Pydantic request/response schemas
├── services/        # Business logic and evaluation engine
migrations/          # Alembic migrations
tests/               # 82 passing tests
```

---

*Built by [Avdhesh Mandloi](https://github.com/avdheshMANDLOI) · 3rd year CSE · IIIT Vadodara*
