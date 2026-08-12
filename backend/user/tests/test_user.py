from datetime import datetime, timedelta, timezone

import jwt
import pytest

from user import security

pytestmark = pytest.mark.asyncio


def _make_token(user_id: int, expired: bool = False) -> str:
    """Build a token the way the auth service would — user service only decodes."""
    delta = timedelta(minutes=-5) if expired else timedelta(minutes=60)
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + delta}
    return jwt.encode(payload, security.JWT_SECRET, algorithm=security.JWT_ALGORITHM)


def _user_record(**overrides):
    record = {
        "id": 1,
        "full_name": "Aziz Karimov",
        "username": "aziz_k",
        "phone": "+998901234567",
        "email": "aziz@example.com",
        "role": "patient",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    record.update(overrides)
    return record


def _auth_header(user_id: int = 1) -> dict:
    return {"Authorization": f"Bearer {_make_token(user_id)}"}


async def test_health_endpoint(client):
    resp = await client.get("/api/v1/user/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- /me ------------------------------------------------------------


async def test_get_me_requires_auth(client):
    resp = await client.get("/api/v1/user/me")
    assert resp.status_code == 401


async def test_get_me_invalid_token_rejected(client):
    resp = await client.get(
        "/api/v1/user/me", headers={"Authorization": "Bearer garbage"}
    )
    assert resp.status_code == 401


async def test_get_me_success(client, patch_db):
    patch_db.get_or_none.return_value = _user_record()
    resp = await client.get("/api/v1/user/me", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Aziz Karimov"


async def test_get_me_staff_role(client, patch_db):
    patch_db.get_or_none.return_value = _user_record(role="staff")
    resp = await client.get("/api/v1/user/me", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["role"] == "staff"


async def test_get_me_user_not_found(client, patch_db):
    patch_db.get_or_none.return_value = None
    resp = await client.get("/api/v1/user/me", headers=_auth_header())
    assert resp.status_code == 401


async def test_update_me(client, patch_db):
    patch_db.get_or_none.return_value = _user_record()
    patch_db.patch.return_value = _user_record(full_name="New Name")

    resp = await client.patch(
        "/api/v1/user/me", json={"full_name": "New Name"}, headers=_auth_header()
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "New Name"

    patch_args = patch_db.patch.call_args
    assert patch_args.args[0] == "/users/1"
    assert patch_args.kwargs["json"] == {"full_name": "New Name"}


async def test_update_me_excludes_unset_fields(client, patch_db):
    patch_db.get_or_none.return_value = _user_record()
    patch_db.patch.return_value = _user_record()

    await client.patch("/api/v1/user/me", json={}, headers=_auth_header())
    patch_args = patch_db.patch.call_args
    assert patch_args.kwargs["json"] == {}


# --- appointments / notifications / discounts ---------------------------------


async def test_get_my_appointments(client, patch_db):
    patch_db.get_or_none.return_value = _user_record()
    patch_db.get.return_value = [
        {
            "id": 1,
            "user_id": 1,
            "hospital_id": None,
            "doctor_id": None,
            "queue_number": None,
            "status": "scheduled",
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    resp = await client.get("/api/v1/user/me/appointments", headers=_auth_header())
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    patch_db.get.assert_called_once_with("/appointments?user_id=1")


async def test_get_my_notifications(client, patch_db):
    patch_db.get_or_none.return_value = _user_record()
    patch_db.get.return_value = [
        {
            "id": 1,
            "user_id": 1,
            "title": "Hi",
            "message": "Hello",
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    resp = await client.get("/api/v1/user/me/notifications", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()[0]["title"] == "Hi"
    patch_db.get.assert_called_once_with("/notifications?user_id=1")


async def test_get_my_discounts(client, patch_db):
    patch_db.get_or_none.return_value = _user_record()
    patch_db.get.return_value = [
        {
            "id": 1,
            "user_id": 1,
            "title": "10% off",
            "code": "SAVE10",
            "percent_off": 10,
            "expires_at": None,
            "is_used": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    resp = await client.get("/api/v1/user/me/discounts", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()[0]["code"] == "SAVE10"
    patch_db.get.assert_called_once_with("/discounts?user_id=1")


async def test_appointments_requires_auth(client):
    resp = await client.get("/api/v1/user/me/appointments")
    assert resp.status_code == 401
