from datetime import datetime, timezone

import pytest

from auth import google_auth, security

pytestmark = pytest.mark.asyncio


def _user_record(**overrides):
    record = {
        "id": 1,
        "full_name": "Aziz Karimov",
        "username": "aziz_k",
        "phone": None,
        "email": None,
        "role": "patient",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "password_hash": None,
    }
    record.update(overrides)
    return record


# --- register ------------------------------------------------------------


async def test_register_creates_user_and_returns_token(client, patch_db):
    patch_db.post.return_value = _user_record()
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Aziz Karimov", "username": "aziz_k", "password": "password123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["username"] == "aziz_k"
    assert body["token_type"] == "bearer"
    assert security.decode_access_token(body["access_token"]) == 1

    posted_kwargs = patch_db.post.call_args.kwargs
    assert posted_kwargs["json"]["username"] == "aziz_k"
    # password must never be forwarded in plaintext, only the hash
    assert "password" not in posted_kwargs["json"]
    assert posted_kwargs["json"]["password_hash"] != "password123"


async def test_register_rejects_short_password(client, patch_db):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Aziz Karimov", "username": "aziz_k", "password": "short"},
    )
    assert resp.status_code == 422
    patch_db.post.assert_not_called()


# --- login ------------------------------------------------------------


async def test_login_success(client, patch_db):
    password_hash = security.hash_password("correct-password")
    patch_db.get_or_none.return_value = _user_record(password_hash=password_hash)

    resp = await client.post(
        "/api/v1/auth/login", json={"username": "aziz_k", "password": "correct-password"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert security.decode_access_token(body["access_token"]) == 1


async def test_login_wrong_password_rejected(client, patch_db):
    password_hash = security.hash_password("correct-password")
    patch_db.get_or_none.return_value = _user_record(password_hash=password_hash)

    resp = await client.post(
        "/api/v1/auth/login", json={"username": "aziz_k", "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_login_unknown_username_rejected(client, patch_db):
    patch_db.get_or_none.return_value = None
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "ghost", "password": "whatever"}
    )
    assert resp.status_code == 401


async def test_login_google_only_account_has_no_password_rejected(client, patch_db):
    patch_db.get_or_none.return_value = _user_record(password_hash=None)
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "aziz_k", "password": "anything"}
    )
    assert resp.status_code == 401


# --- me ------------------------------------------------------------


async def test_get_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401  # no bearer credentials supplied


async def test_get_me_with_valid_token(client, patch_db):
    token = security.create_access_token(1)
    patch_db.get_or_none.return_value = _user_record()
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "aziz_k"


async def test_get_me_invalid_token_rejected(client):
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer garbage-token"}
    )
    assert resp.status_code == 401


async def test_get_me_user_no_longer_exists(client, patch_db):
    token = security.create_access_token(999)
    patch_db.get_or_none.return_value = None
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


# --- google login ------------------------------------------------------------


async def test_google_login_not_configured_returns_500(client, monkeypatch):
    monkeypatch.setattr(google_auth, "is_configured", lambda: False)
    resp = await client.get("/api/v1/auth/google/login")
    assert resp.status_code == 500


async def test_google_login_configured_redirects(client, monkeypatch):
    monkeypatch.setattr(google_auth, "is_configured", lambda: True)
    monkeypatch.setattr(
        google_auth, "build_authorization_url", lambda: "https://accounts.google.com/fake"
    )
    resp = await client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"] == "https://accounts.google.com/fake"


async def test_google_test_page_reflects_configuration(client, monkeypatch):
    monkeypatch.setattr(google_auth, "is_configured", lambda: False)
    resp = await client.get("/api/v1/auth/google/test")
    assert resp.status_code == 200
    assert "not configured" in resp.text


# --- google callback ------------------------------------------------------------


async def test_google_callback_invalid_state_rejected(client, monkeypatch):
    monkeypatch.setattr(google_auth, "verify_state", lambda state: False)
    resp = await client.get("/api/v1/auth/callback", params={"code": "abc", "state": "bad"})
    assert resp.status_code == 400


async def test_google_callback_unverified_email_rejected(client, monkeypatch):
    monkeypatch.setattr(google_auth, "verify_state", lambda state: True)

    async def fake_exchange_code(code):
        return {"id_token": "fake-jwt"}

    monkeypatch.setattr(google_auth, "exchange_code", fake_exchange_code)
    monkeypatch.setattr(
        google_auth,
        "verify_id_token",
        lambda token: {"email": "a@x.com", "email_verified": False},
    )
    resp = await client.get("/api/v1/auth/callback", params={"code": "abc", "state": "good"})
    assert resp.status_code == 403


async def test_google_callback_existing_user_logs_in(client, monkeypatch, patch_db):
    monkeypatch.setattr(google_auth, "verify_state", lambda state: True)

    async def fake_exchange_code(code):
        return {"id_token": "fake-jwt"}

    monkeypatch.setattr(google_auth, "exchange_code", fake_exchange_code)
    monkeypatch.setattr(
        google_auth,
        "verify_id_token",
        lambda token: {"email": "a@x.com", "email_verified": True, "name": "A"},
    )
    patch_db.get_or_none.return_value = _user_record(email="a@x.com")

    resp = await client.get("/api/v1/auth/callback", params={"code": "abc", "state": "good"})
    assert resp.status_code == 200
    patch_db.post.assert_not_called()


async def test_google_callback_new_user_registers(client, monkeypatch, patch_db):
    monkeypatch.setattr(google_auth, "verify_state", lambda state: True)

    async def fake_exchange_code(code):
        return {"id_token": "fake-jwt"}

    monkeypatch.setattr(google_auth, "exchange_code", fake_exchange_code)
    monkeypatch.setattr(
        google_auth,
        "verify_id_token",
        lambda token: {"email": "new@x.com", "email_verified": True, "name": "New User"},
    )
    patch_db.get_or_none.return_value = None
    patch_db.post.return_value = _user_record(id=2, email="new@x.com", username=None, full_name="New User")

    resp = await client.get("/api/v1/auth/callback", params={"code": "abc", "state": "good"})
    assert resp.status_code == 200
    patch_db.post.assert_called_once()
    assert resp.json()["user"]["email"] == "new@x.com"


# --- health ------------------------------------------------------------


async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
