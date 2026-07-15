"""
End-to-end analytics pipeline test.

Simulates the full flow:
  1. Create project + flag + API key (JWT auth)
  2. Directly ingest evaluation events (simulating SDK flush)
  3. Verify counts appear in the analytics query API

Why not use the real SDK here?
  The backend test suite uses SQLite in-memory with no running server.
  The SDK talks HTTP to a real server. Mixing them in one test would
  require a live server, which makes CI fragile.
  Instead we test the full backend pipeline (ingest → aggregate → query)
  and trust the SDK tests cover the buffering + flush side.
"""
import pytest
from uuid import UUID
from datetime import datetime, timezone, timedelta

pytestmark = pytest.mark.asyncio


async def _bootstrap(client, suffix: str = "1") -> tuple[str, str, str]:
    """
    Register user, create project + flag + API key.
    Returns (jwt_token, sdk_key, project_id).
    """
    email = f"e2e_{suffix}@analytics.com"
    project_name = f"e2e-project-{suffix}"

    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "E2E User",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "password123",
    })
    token = resp.json()["access_token"]

    proj = await client.post("/api/v1/projects",
        json={"name": project_name, "display_name": "E2E Project"},
        headers={"Authorization": f"Bearer {token}"},
    )
    project_id = proj.json()["id"]

    await client.post(f"/api/v1/projects/{project_id}/flags",
        json={"name": "checkout-v2", "display_name": "Checkout V2"},
        headers={"Authorization": f"Bearer {token}"},
    )

    key_resp = await client.post(f"/api/v1/projects/{project_id}/api-keys",
        json={"name": "e2e-key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    sdk_key = key_resp.json()["key"]

    return token, sdk_key, project_id


@pytest.mark.asyncio
async def test_full_analytics_pipeline(client, db_session):
    token, sdk_key, project_id = await _bootstrap(client, "1")

    from app.repositories.event_repo import EventRepository
    repo = EventRepository(db_session)
    events = (
        [{"flag_key": "checkout-v2", "variation": "true", "user_key": f"u{i}", "timestamp": None}
         for i in range(7)]
        +
        [{"flag_key": "checkout-v2", "variation": "false", "user_key": f"u{i+7}", "timestamp": None}
         for i in range(3)]
    )
    await repo.ingest_batch(project_id=UUID(project_id), events=events)

    resp = await client.get(
        f"/api/v1/analytics/projects/{project_id}/flags/checkout-v2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_evaluations"] == 10
    assert data["flag_key"] == "checkout-v2"
    assert len(data["buckets"]) == 2


@pytest.mark.asyncio
async def test_full_analytics_summary(client, db_session):
    token, sdk_key, project_id = await _bootstrap(client, "2")

    from app.repositories.event_repo import EventRepository
    repo = EventRepository(db_session)
    events = (
        [{"flag_key": "checkout-v2", "variation": "true", "user_key": f"u{i}", "timestamp": None}
         for i in range(3)]
        +
        [{"flag_key": "checkout-v2", "variation": "false", "user_key": f"u{i+3}", "timestamp": None}
         for i in range(1)]
    )
    await repo.ingest_batch(project_id=UUID(project_id), events=events)

    resp = await client.get(
        f"/api/v1/analytics/projects/{project_id}/flags/checkout-v2/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_evaluations"] == 4

    variations = {v["variation"]: v for v in data["variations"]}
    assert variations["true"]["count"] == 3
    assert variations["false"]["count"] == 1
    assert abs(variations["true"]["percentage"] - 75.0) < 0.01
    assert abs(variations["false"]["percentage"] - 25.0) < 0.01


@pytest.mark.asyncio
async def test_ingestion_endpoint_accepts_and_returns_202(client, db_session):
    token, sdk_key, project_id = await _bootstrap(client, "3")

    resp = await client.post("/api/v1/analytics/events",
        json={"events": [
            {"flag_key": "checkout-v2", "variation": "true", "user_key": "user-1"},
            {"flag_key": "checkout-v2", "variation": "true", "user_key": "user-2"},
            {"flag_key": "checkout-v2", "variation": "false", "user_key": "user-3"},
        ]},
        headers={"Authorization": f"Bearer {sdk_key}"},
    )
    assert resp.status_code == 202
    assert resp.json()["received"] == 3


@pytest.mark.asyncio
async def test_analytics_project_isolation(client, db_session):
    """
    Events for project A must not appear in project B's analytics.
    """
    # Project A
    await client.post("/api/v1/auth/register", json={
        "email": "e2e_a@analytics.com", "password": "password123", "name": "User A"
    })
    resp_a = await client.post("/api/v1/auth/login", json={
        "email": "e2e_a@analytics.com", "password": "password123"
    })
    token_a = resp_a.json()["access_token"]
    proj_a = await client.post("/api/v1/projects",
        json={"name": "project-a", "display_name": "Project A"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    project_id_a = proj_a.json()["id"]
    await client.post(f"/api/v1/projects/{project_id_a}/flags",
        json={"name": "shared-flag", "display_name": "Shared Flag"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # Project B
    await client.post("/api/v1/auth/register", json={
        "email": "e2e_b@analytics.com", "password": "password123", "name": "User B"
    })
    resp_b = await client.post("/api/v1/auth/login", json={
        "email": "e2e_b@analytics.com", "password": "password123"
    })
    token_b = resp_b.json()["access_token"]
    proj_b = await client.post("/api/v1/projects",
        json={"name": "project-b", "display_name": "Project B"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    project_id_b = proj_b.json()["id"]
    await client.post(f"/api/v1/projects/{project_id_b}/flags",
        json={"name": "shared-flag", "display_name": "Shared Flag"},
        headers={"Authorization": f"Bearer {token_b}"},
    )

    # Ingest 5 events into project A only
    from app.repositories.event_repo import EventRepository
    repo = EventRepository(db_session)
    await repo.ingest_batch(
        project_id=UUID(project_id_a),
        events=[
            {"flag_key": "shared-flag", "variation": "true", "user_key": f"u{i}", "timestamp": None}
            for i in range(5)
        ]
    )

    # Project A should see 5 evaluations
    resp = await client.get(
        f"/api/v1/analytics/projects/{project_id_a}/flags/shared-flag",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.json()["total_evaluations"] == 5

    # Project B should see 0 evaluations
    resp = await client.get(
        f"/api/v1/analytics/projects/{project_id_b}/flags/shared-flag",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.json()["total_evaluations"] == 0