"""
Integration tests for Phase 3 endpoints.

Tests: Flag CRUD, API Key CRUD, Rules CRUD, Evaluation endpoint.
Uses the same in-memory SQLite setup as Phase 2 tests.
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


async def create_project(client: AsyncClient, token: str, name: str = None) -> dict:
    import uuid
    project_name = name or f"Project {uuid.uuid4().hex[:8]}"
    resp = await client.post(
        PROJECTS_URL,
        json={"name": project_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"Project creation failed: {resp.json()}"
    return resp.json()


def flags_url(project_id: str) -> str:
    return f"/api/v1/projects/{project_id}/flags"


def api_keys_url(project_id: str) -> str:
    return f"/api/v1/projects/{project_id}/api-keys"


def rules_url(flag_id: str) -> str:
    return f"/api/v1/flags/{flag_id}/rules"


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def api_key_auth(key: str) -> dict:
    return {"Authorization": f"Bearer {key}"}


# ── Flag CRUD ─────────────────────────────────────────────────────────────────

async def test_create_flag_success(client: AsyncClient):
    token = await register_and_get_token(client, "flagcreate@test.com")
    project = await create_project(client, token)

    resp = await client.post(
        flags_url(project["id"]),
        json={"name": "new_checkout", "display_name": "New Checkout UI"},
        headers=auth(token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "new_checkout"
    assert body["is_enabled"] is False
    assert body["rollout_percentage"] == 0


async def test_create_flag_invalid_name(client: AsyncClient):
    token = await register_and_get_token(client, "flagname@test.com")
    project = await create_project(client, token)

    resp = await client.post(
        flags_url(project["id"]),
        json={"name": "Invalid Name!", "display_name": "Bad"},
        headers=auth(token),
    )
    assert resp.status_code == 422


async def test_create_flag_duplicate_name(client: AsyncClient):
    token = await register_and_get_token(client, "flagdup@test.com")
    project = await create_project(client, token)

    await client.post(
        flags_url(project["id"]),
        json={"name": "my_flag", "display_name": "My Flag"},
        headers=auth(token),
    )
    resp = await client.post(
        flags_url(project["id"]),
        json={"name": "my_flag", "display_name": "My Flag 2"},
        headers=auth(token),
    )
    assert resp.status_code == 409


async def test_update_flag_enable(client: AsyncClient):
    token = await register_and_get_token(client, "flagupdate@test.com")
    project = await create_project(client, token)
    flag = (await client.post(
        flags_url(project["id"]),
        json={"name": "toggle_me", "display_name": "Toggle Me"},
        headers=auth(token),
    )).json()

    resp = await client.patch(
        f"/api/v1/projects/{project['id']}/flags/{flag['id']}",
        json={"is_enabled": True, "rollout_percentage": 50},
        headers=auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["is_enabled"] is True
    assert resp.json()["rollout_percentage"] == 50


async def test_delete_flag_soft_deletes(client: AsyncClient):
    token = await register_and_get_token(client, "flagdelete@test.com")
    project = await create_project(client, token)
    flag = (await client.post(
        flags_url(project["id"]),
        json={"name": "delete_me", "display_name": "Delete Me"},
        headers=auth(token),
    )).json()

    resp = await client.delete(
        f"/api/v1/projects/{project['id']}/flags/{flag['id']}",
        headers=auth(token),
    )
    assert resp.status_code == 204

    # Should no longer appear in list
    list_resp = await client.get(flags_url(project["id"]), headers=auth(token))
    flag_ids = [f["id"] for f in list_resp.json()["flags"]]
    assert flag["id"] not in flag_ids


# ── API Key CRUD ──────────────────────────────────────────────────────────────

async def test_generate_api_key(client: AsyncClient):
    token = await register_and_get_token(client, "keygen@test.com")
    project = await create_project(client, token)

    resp = await client.post(
        api_keys_url(project["id"]),
        json={"label": "Production"},
        headers=auth(token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "key" in body
    assert body["key"].startswith("proj_sk_")
    assert body["label"] == "Production"


async def test_api_key_not_shown_in_list(client: AsyncClient):
    token = await register_and_get_token(client, "keylist@test.com")
    project = await create_project(client, token)

    created = (await client.post(
        api_keys_url(project["id"]),
        json={"label": "Staging"},
        headers=auth(token),
    )).json()

    list_resp = await client.get(api_keys_url(project["id"]), headers=auth(token))
    assert list_resp.status_code == 200
    keys = list_resp.json()
    assert len(keys) == 1
    # Full key must not appear in list
    assert "key" not in keys[0]
    assert keys[0]["key_prefix"] == created["key_prefix"]


async def test_revoke_api_key(client: AsyncClient):
    token = await register_and_get_token(client, "keyrevoke@test.com")
    project = await create_project(client, token)

    created = (await client.post(
        api_keys_url(project["id"]),
        json={"label": "To Revoke"},
        headers=auth(token),
    )).json()

    resp = await client.delete(
        f"{api_keys_url(project['id'])}/{created['id']}",
        headers=auth(token),
    )
    assert resp.status_code == 204


# ── Targeting Rules ───────────────────────────────────────────────────────────

async def test_create_rule(client: AsyncClient):
    token = await register_and_get_token(client, "rulecreate@test.com")
    project = await create_project(client, token)
    flag = (await client.post(
        flags_url(project["id"]),
        json={"name": "rule_flag", "display_name": "Rule Flag"},
        headers=auth(token),
    )).json()

    resp = await client.post(
        rules_url(flag["id"]),
        json={
            "rule_type": "user_id",
            "operator": "in_list",
            "value": ["user_1", "user_2"],
            "effect": "include",
            "priority": 0,
        },
        headers=auth(token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["rule_type"] == "user_id"
    assert body["effect"] == "include"


async def test_create_rule_invalid_operator(client: AsyncClient):
    token = await register_and_get_token(client, "ruleinvalid@test.com")
    project = await create_project(client, token)
    flag = (await client.post(
        flags_url(project["id"]),
        json={"name": "rule_flag2", "display_name": "Rule Flag 2"},
        headers=auth(token),
    )).json()

    resp = await client.post(
        rules_url(flag["id"]),
        json={
            "rule_type": "user_id",
            "operator": "contains",  # v2 only
            "value": "admin",
            "effect": "include",
        },
        headers=auth(token),
    )
    assert resp.status_code == 422


async def test_delete_rule(client: AsyncClient):
    token = await register_and_get_token(client, "ruledelete@test.com")
    project = await create_project(client, token)
    flag = (await client.post(
        flags_url(project["id"]),
        json={"name": "rule_del_flag", "display_name": "Rule Del Flag"},
        headers=auth(token),
    )).json()

    rule = (await client.post(
        rules_url(flag["id"]),
        json={"rule_type": "user_id", "operator": "equals", "value": "u1", "effect": "exclude"},
        headers=auth(token),
    )).json()

    resp = await client.delete(f"{rules_url(flag['id'])}/{rule['id']}", headers=auth(token))
    assert resp.status_code == 204


# ── Evaluation endpoint ───────────────────────────────────────────────────────

async def _setup_flag_with_api_key(client, email, flag_name="eval_flag", rollout=100):
    """Helper: register user, create project + flag + api key, enable flag."""
    token = await register_and_get_token(client, email)
    project = await create_project(client, token)

    flag = (await client.post(
        flags_url(project["id"]),
        json={"name": flag_name, "display_name": "Eval Flag", "rollout_percentage": rollout},
        headers=auth(token),
    )).json()

    # Enable the flag
    await client.patch(
        f"/api/v1/projects/{project['id']}/flags/{flag['id']}",
        json={"is_enabled": True},
        headers=auth(token),
    )

    api_key_resp = (await client.post(
        api_keys_url(project["id"]),
        json={"label": "Test"},
        headers=auth(token),
    )).json()

    return api_key_resp["key"], flag["id"]


async def test_evaluate_flag_enabled_100_percent(client: AsyncClient):
    api_key, _ = await _setup_flag_with_api_key(client, "eval100@test.com", rollout=100)

    resp = await client.post(
        "/api/v1/evaluate",
        json={"flag_name": "eval_flag", "user_id": "user_123"},
        headers=api_key_auth(api_key),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is True
    assert body["reason"] == "rollout_included"
    assert body["flag_name"] == "eval_flag"


async def test_evaluate_flag_disabled(client: AsyncClient):
    token = await register_and_get_token(client, "evaldisabled@test.com")
    project = await create_project(client, token)

    await client.post(
        flags_url(project["id"]),
        json={"name": "off_flag", "display_name": "Off Flag"},
        headers=auth(token),
    )
    # Flag is disabled by default (is_enabled=False)

    api_key = (await client.post(
        api_keys_url(project["id"]),
        json={"label": "Test"},
        headers=auth(token),
    )).json()["key"]

    resp = await client.post(
        "/api/v1/evaluate",
        json={"flag_name": "off_flag", "user_id": "user_1"},
        headers=api_key_auth(api_key),
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False
    assert resp.json()["reason"] == "flag_disabled"


async def test_evaluate_flag_not_found(client: AsyncClient):
    token = await register_and_get_token(client, "evalnotfound@test.com")
    project = await create_project(client, token)

    api_key = (await client.post(
        api_keys_url(project["id"]),
        json={"label": "Test"},
        headers=auth(token),
    )).json()["key"]

    resp = await client.post(
        "/api/v1/evaluate",
        json={"flag_name": "does_not_exist", "user_id": "user_1"},
        headers=api_key_auth(api_key),
    )
    assert resp.status_code == 200  # Never 404 — graceful degradation
    assert resp.json()["enabled"] is False
    assert resp.json()["reason"] == "flag_not_found"


async def test_evaluate_requires_api_key_not_jwt(client: AsyncClient):
    token = await register_and_get_token(client, "evaljwt@test.com")

    # JWT token should NOT work on the evaluate endpoint
    resp = await client.post(
        "/api/v1/evaluate",
        json={"flag_name": "any_flag", "user_id": "user_1"},
        headers=auth(token),  # This is a JWT, not an API key
    )
    # Should get 401 — JWT is not a valid API key
    assert resp.status_code == 401


async def test_evaluate_invalid_api_key(client: AsyncClient):
    resp = await client.post(
        "/api/v1/evaluate",
        json={"flag_name": "any_flag", "user_id": "user_1"},
        headers=api_key_auth("proj_sk_fakekeyhere"),
    )
    assert resp.status_code == 401
