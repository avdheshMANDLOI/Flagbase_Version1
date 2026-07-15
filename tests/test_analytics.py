"""
Phase 1 analytics tests — batch ingestion endpoint.
"""
import pytest

pytestmark = pytest.mark.asyncio


async def _setup(client, suffix: str) -> tuple[str, str]:
    """Returns (sdk_key, jwt_token)."""
    email = f"analytics_{suffix}@test.com"
    project_name = f"analytics-project-{suffix}"

    await client.post("/api/v1/auth/register", json={
        "email": email, "password": "password123", "name": "Analytics User"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email, "password": "password123"
    })
    token = resp.json()["access_token"]

    proj = await client.post("/api/v1/projects",
        json={"name": project_name, "display_name": "Analytics Project"},
        headers={"Authorization": f"Bearer {token}"}
    )
    project_id = proj.json()["id"]

    await client.post(f"/api/v1/projects/{project_id}/flags",
        json={"name": "test-flag", "display_name": "Test Flag"},
        headers={"Authorization": f"Bearer {token}"}
    )

    key_resp = await client.post(f"/api/v1/projects/{project_id}/api-keys",
        json={"name": "test-key"},
        headers={"Authorization": f"Bearer {token}"}
    )
    return key_resp.json()["key"], token


async def _setup_with_project(client, suffix: str) -> tuple[str, str, str]:
    """Returns (sdk_key, jwt_token, project_id)."""
    email = f"analytics_{suffix}@test.com"
    project_name = f"analytics-project-{suffix}"

    await client.post("/api/v1/auth/register", json={
        "email": email, "password": "password123", "name": "Analytics User"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email, "password": "password123"
    })
    token = resp.json()["access_token"]

    proj = await client.post("/api/v1/projects",
        json={"name": project_name, "display_name": "Analytics Project"},
        headers={"Authorization": f"Bearer {token}"}
    )
    project_id = proj.json()["id"]

    await client.post(f"/api/v1/projects/{project_id}/flags",
        json={"name": "test-flag", "display_name": "Test Flag"},
        headers={"Authorization": f"Bearer {token}"}
    )

    key_resp = await client.post(f"/api/v1/projects/{project_id}/api-keys",
        json={"name": "test-key"},
        headers={"Authorization": f"Bearer {token}"}
    )
    return key_resp.json()["key"], token, project_id


@pytest.mark.asyncio
async def test_ingest_events_returns_202(client):
    sdk_key, _ = await _setup(client, "1")

    resp = await client.post("/api/v1/analytics/events",
        json={"events": [{"flag_key": "test-flag", "variation": "true", "user_key": "user-1"}]},
        headers={"Authorization": f"Bearer {sdk_key}"}
    )
    assert resp.status_code == 202
    assert resp.json()["received"] == 1


@pytest.mark.asyncio
async def test_ingest_batch_multiple_events(client):
    sdk_key, _ = await _setup(client, "2")

    events = [
        {"flag_key": "test-flag", "variation": "true", "user_key": f"user-{i}"}
        for i in range(5)
    ]
    resp = await client.post("/api/v1/analytics/events",
        json={"events": events},
        headers={"Authorization": f"Bearer {sdk_key}"}
    )
    assert resp.status_code == 202
    assert resp.json()["received"] == 5


@pytest.mark.asyncio
async def test_ingest_unknown_flag_silently_dropped(client):
    sdk_key, _ = await _setup(client, "3")

    resp = await client.post("/api/v1/analytics/events",
        json={"events": [{"flag_key": "ghost-flag", "variation": "true", "user_key": "user-1"}]},
        headers={"Authorization": f"Bearer {sdk_key}"}
    )
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_ingest_requires_api_key(client):
    resp = await client.post("/api/v1/analytics/events",
        json={"events": [{"flag_key": "test-flag", "variation": "true", "user_key": "user-1"}]},
        headers={"Authorization": "Bearer invalid-key"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ingest_empty_events_rejected(client):
    sdk_key, _ = await _setup(client, "4")

    resp = await client.post("/api/v1/analytics/events",
        json={"events": []},
        headers={"Authorization": f"Bearer {sdk_key}"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_jwt_token_rejected_on_analytics_endpoint(client):
    """Analytics endpoint only accepts SDK API keys, not JWT tokens."""
    _, token = await _setup(client, "5")

    resp = await client.post("/api/v1/analytics/events",
        json={"events": [{"flag_key": "test-flag", "variation": "true", "user_key": "user-1"}]},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401

# ── Phase 3: Query API tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_timeseries_returns_empty_buckets_for_no_data(client):
    sdk_key, token, project_id = await _setup_with_project(client, "6")

    resp = await client.get(
        f"/api/v1/analytics/projects/{project_id}/flags/test-flag",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["flag_key"] == "test-flag"
    assert data["total_evaluations"] == 0
    assert data["buckets"] == []


@pytest.mark.asyncio
async def test_timeseries_returns_data_after_ingestion(client, db_session):
    sdk_key, token, project_id = await _setup_with_project(client, "7")

    # Ingest directly via repo (bypasses queue — tests have no running worker)
    from uuid import UUID
    from app.repositories.event_repo import EventRepository
    repo = EventRepository(db_session)
    await repo.ingest_batch(
        project_id=UUID(project_id),
        events=[
            {"flag_key": "test-flag", "variation": "true", "user_key": "u1", "timestamp": None},
            {"flag_key": "test-flag", "variation": "true", "user_key": "u2", "timestamp": None},
            {"flag_key": "test-flag", "variation": "false", "user_key": "u3", "timestamp": None},
        ]
    )

    resp = await client.get(
        f"/api/v1/analytics/projects/{project_id}/flags/test-flag",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_evaluations"] == 3
    assert len(data["buckets"]) == 2

@pytest.mark.asyncio
async def test_summary_percentage_adds_up(client, db_session):
    sdk_key, token, project_id = await _setup_with_project(client, "8")

    from uuid import UUID
    from app.repositories.event_repo import EventRepository
    repo = EventRepository(db_session)
    await repo.ingest_batch(
        project_id=UUID(project_id),
        events=[
            {"flag_key": "test-flag", "variation": "true", "user_key": "u1", "timestamp": None},
            {"flag_key": "test-flag", "variation": "true", "user_key": "u2", "timestamp": None},
            {"flag_key": "test-flag", "variation": "true", "user_key": "u3", "timestamp": None},
            {"flag_key": "test-flag", "variation": "false", "user_key": "u4", "timestamp": None},
        ]
    )

    resp = await client.get(
        f"/api/v1/analytics/projects/{project_id}/flags/test-flag/summary",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_evaluations"] == 4
    total_pct = sum(v["percentage"] for v in data["variations"])
    assert abs(total_pct - 100.0) < 0.01


@pytest.mark.asyncio
async def test_timeseries_flag_not_found_returns_404(client):
    sdk_key, token, project_id = await _setup_with_project(client, "9")

    resp = await client.get(
        f"/api/v1/analytics/projects/{project_id}/flags/nonexistent-flag",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_query_requires_jwt_not_api_key(client):
    sdk_key, token, project_id = await _setup_with_project(client, "10")

    resp = await client.get(
        f"/api/v1/analytics/projects/{project_id}/flags/test-flag",
        headers={"Authorization": f"Bearer {sdk_key}"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_summary_empty_returns_zero(client):
    sdk_key, token, project_id = await _setup_with_project(client, "11")

    resp = await client.get(
        f"/api/v1/analytics/projects/{project_id}/flags/test-flag/summary",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_evaluations"] == 0
    assert data["variations"] == []