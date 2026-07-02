"""
Tests for POST   /api/v1/projects
         GET    /api/v1/projects
         GET    /api/v1/projects/{id}
         PATCH  /api/v1/projects/{id}
         DELETE /api/v1/projects/{id}
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

REGISTER_URL = "/api/v1/auth/register"
PROJECTS_URL = "/api/v1/projects"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def register_and_get_token(client: AsyncClient, email="user@test.com") -> str:
    resp = await client.post(REGISTER_URL, json={
        "email": email, "name": "Test User", "password": "password123"
    })
    return resp.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Create ────────────────────────────────────────────────────────────────────

async def test_create_project_success(client: AsyncClient):
    token = await register_and_get_token(client)
    resp = await client.post(PROJECTS_URL, json={"name": "My App"}, headers=auth(token))
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "My App"
    assert body["slug"] == "my-app"
    assert body["is_active"] is True


async def test_create_project_custom_slug(client: AsyncClient):
    token = await register_and_get_token(client, "slug@test.com")
    resp = await client.post(PROJECTS_URL, json={"name": "My App", "slug": "custom-slug"}, headers=auth(token))
    assert resp.status_code == 201
    assert resp.json()["slug"] == "custom-slug"


async def test_create_project_duplicate_slug(client: AsyncClient):
    token = await register_and_get_token(client, "dup@test.com")
    await client.post(PROJECTS_URL, json={"name": "My App"}, headers=auth(token))
    resp = await client.post(PROJECTS_URL, json={"name": "My App"}, headers=auth(token))
    assert resp.status_code == 409


async def test_create_project_requires_auth(client: AsyncClient):
    resp = await client.post(PROJECTS_URL, json={"name": "My App"})
    assert resp.status_code == 403


async def test_create_project_invalid_slug(client: AsyncClient):
    token = await register_and_get_token(client, "badslug@test.com")
    resp = await client.post(PROJECTS_URL, json={"name": "x", "slug": "BAD SLUG!"}, headers=auth(token))
    assert resp.status_code == 422


# ── List ──────────────────────────────────────────────────────────────────────

async def test_list_projects_empty(client: AsyncClient):
    token = await register_and_get_token(client, "empty@test.com")
    resp = await client.get(PROJECTS_URL, headers=auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_projects_returns_owned_only(client: AsyncClient):
    token_a = await register_and_get_token(client, "a@test.com")
    token_b = await register_and_get_token(client, "b@test.com")

    await client.post(PROJECTS_URL, json={"name": "User A Project"}, headers=auth(token_a))
    await client.post(PROJECTS_URL, json={"name": "User B Project"}, headers=auth(token_b))

    resp = await client.get(PROJECTS_URL, headers=auth(token_a))
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "User A Project" in names
    assert "User B Project" not in names


# ── Get ───────────────────────────────────────────────────────────────────────

async def test_get_project_success(client: AsyncClient):
    token = await register_and_get_token(client, "get@test.com")
    created = (await client.post(PROJECTS_URL, json={"name": "Get Me"}, headers=auth(token))).json()
    resp = await client.get(f"{PROJECTS_URL}/{created['id']}", headers=auth(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


async def test_get_project_not_owned(client: AsyncClient):
    token_a = await register_and_get_token(client, "owner@test.com")
    token_b = await register_and_get_token(client, "other@test.com")
    created = (await client.post(PROJECTS_URL, json={"name": "Private"}, headers=auth(token_a))).json()
    resp = await client.get(f"{PROJECTS_URL}/{created['id']}", headers=auth(token_b))
    assert resp.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

async def test_update_project_name(client: AsyncClient):
    token = await register_and_get_token(client, "update@test.com")
    created = (await client.post(PROJECTS_URL, json={"name": "Old Name"}, headers=auth(token))).json()
    resp = await client.patch(
        f"{PROJECTS_URL}/{created['id']}", json={"name": "New Name"}, headers=auth(token)
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    # slug should NOT change on update
    assert resp.json()["slug"] == created["slug"]


async def test_update_project_not_owned(client: AsyncClient):
    token_a = await register_and_get_token(client, "patchowner@test.com")
    token_b = await register_and_get_token(client, "patchother@test.com")
    created = (await client.post(PROJECTS_URL, json={"name": "Mine"}, headers=auth(token_a))).json()
    resp = await client.patch(
        f"{PROJECTS_URL}/{created['id']}", json={"name": "Stolen"}, headers=auth(token_b)
    )
    assert resp.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

async def test_delete_project_success(client: AsyncClient):
    token = await register_and_get_token(client, "delete@test.com")
    created = (await client.post(PROJECTS_URL, json={"name": "Delete Me"}, headers=auth(token))).json()
    resp = await client.delete(f"{PROJECTS_URL}/{created['id']}", headers=auth(token))
    assert resp.status_code == 204
    # Should no longer appear in list
    projects = (await client.get(PROJECTS_URL, headers=auth(token))).json()
    assert not any(p["id"] == created["id"] for p in projects)


async def test_delete_project_not_owned(client: AsyncClient):
    token_a = await register_and_get_token(client, "delowner@test.com")
    token_b = await register_and_get_token(client, "delother@test.com")
    created = (await client.post(PROJECTS_URL, json={"name": "Not Yours"}, headers=auth(token_a))).json()
    resp = await client.delete(f"{PROJECTS_URL}/{created['id']}", headers=auth(token_b))
    assert resp.status_code == 404
