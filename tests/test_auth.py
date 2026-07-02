"""
Tests for POST /api/v1/auth/register
         POST /api/v1/auth/login
         GET  /api/v1/auth/me
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"

VALID_USER = {
    "email": "avdhesh@example.com",
    "name": "Avdhesh",
    "password": "securepassword123",
}


# ── Register ──────────────────────────────────────────────────────────────────

async def test_register_success(client: AsyncClient):
    resp = await client.post(REGISTER_URL, json=VALID_USER)
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


async def test_register_duplicate_email(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_USER)
    resp = await client.post(REGISTER_URL, json=VALID_USER)
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


async def test_register_invalid_email(client: AsyncClient):
    resp = await client.post(REGISTER_URL, json={**VALID_USER, "email": "not-an-email"})
    assert resp.status_code == 422


async def test_register_password_too_short(client: AsyncClient):
    resp = await client.post(REGISTER_URL, json={**VALID_USER, "password": "short"})
    assert resp.status_code == 422


async def test_register_empty_name(client: AsyncClient):
    resp = await client.post(REGISTER_URL, json={**VALID_USER, "name": "   "})
    assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

async def test_login_success(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_USER)
    resp = await client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "password": VALID_USER["password"],
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_USER)
    resp = await client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


async def test_login_nonexistent_email(client: AsyncClient):
    resp = await client.post(LOGIN_URL, json={
        "email": "nobody@example.com",
        "password": "whatever",
    })
    assert resp.status_code == 401


async def test_login_email_case_insensitive(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_USER)
    resp = await client.post(LOGIN_URL, json={
        "email": VALID_USER["email"].upper(),
        "password": VALID_USER["password"],
    })
    assert resp.status_code == 200


# ── Me ────────────────────────────────────────────────────────────────────────

async def test_me_returns_profile(client: AsyncClient):
    user = {**VALID_USER, "email": "me_test@example.com"}
    reg = await client.post(REGISTER_URL, json=user)
    token = reg.json()["access_token"]
    resp = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me_test@example.com"
    assert body["name"] == VALID_USER["name"]
    assert "password" not in body
    assert "password_hash" not in body


async def test_me_requires_auth(client: AsyncClient):
    resp = await client.get(ME_URL)
    assert resp.status_code == 403


async def test_me_invalid_token(client: AsyncClient):
    resp = await client.get(ME_URL, headers={"Authorization": "Bearer fake.token.here"})
    assert resp.status_code == 401
