"""
Phase 1 analytics tests — batch ingestion endpoint.
"""
import pytest

pytestmark = pytest.mark.asyncio


async def _setup(client, suffix: str) -> str:
    """Register a unique user, create a project, flag, and API key. Returns sdk_key."""
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