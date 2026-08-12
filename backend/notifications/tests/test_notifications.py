from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import jwt
import pytest

from notifications import push, security

pytestmark = pytest.mark.asyncio


def _make_token(user_id: int, expired: bool = False) -> str:
    delta = timedelta(minutes=-5) if expired else timedelta(minutes=60)
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + delta}
    return jwt.encode(payload, security.JWT_SECRET, algorithm=security.JWT_ALGORITHM)


def _auth_header(user_id: int = 1) -> dict:
    return {"Authorization": f"Bearer {_make_token(user_id)}"}


def _user(**overrides):
    record = {"id": 1, "role": "patient"}
    record.update(overrides)
    return record


def _subscription(**overrides):
    record = {
        "id": 1,
        "user_id": 1,
        "endpoint": "https://push.example.com/abc",
        "p256dh": "p256dh-key",
        "auth_key": "auth-key",
    }
    record.update(overrides)
    return record


def _notification(**overrides):
    record = {
        "id": 1,
        "user_id": 1,
        "title": "Share your feedback",
        "message": "Tell us about your recent visit",
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    record.update(overrides)
    return record


def _get_or_none_router(user=None, notification=None):
    async def _dispatch(path):
        if path.startswith("/users/"):
            return user
        if path.startswith("/notifications/"):
            return notification
        return None

    return _dispatch


async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- list notifications ----------------------------------------------------


async def test_list_notifications_requires_auth(client):
    resp = await client.get("/api/notifications")
    assert resp.status_code == 401


async def test_list_notifications_invalid_token(client):
    resp = await client.get(
        "/api/notifications", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


async def test_list_notifications_user_not_found(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=None)
    resp = await client.get("/api/notifications", headers=_auth_header())
    assert resp.status_code == 401


async def test_list_notifications_success(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user())
    patch_db.get.return_value = [_notification()]
    resp = await client.get("/api/notifications", headers=_auth_header())
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == 1

    called_path = patch_db.get.call_args.args[0]
    assert called_path.startswith("/notifications?")
    assert "user_id=1" in called_path


async def test_list_notifications_pagination_params(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user())
    patch_db.get.return_value = []
    resp = await client.get(
        "/api/notifications?limit=10&offset=5", headers=_auth_header()
    )
    assert resp.status_code == 200
    called_path = patch_db.get.call_args.args[0]
    assert "limit=10" in called_path
    assert "offset=5" in called_path


# --- mark notification read -------------------------------------------------


async def test_mark_notification_read_requires_auth(client):
    resp = await client.patch("/api/notifications/1/read")
    assert resp.status_code == 401


async def test_mark_notification_read_not_found(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(), notification=None)
    resp = await client.patch("/api/notifications/1/read", headers=_auth_header())
    assert resp.status_code == 404


async def test_mark_notification_read_not_your_notification(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(), notification=_notification(user_id=999)
    )
    resp = await client.patch("/api/notifications/1/read", headers=_auth_header())
    assert resp.status_code == 404


async def test_mark_notification_read_success(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(), notification=_notification(user_id=1, is_read=False)
    )
    patch_db.patch.return_value = _notification(user_id=1, is_read=True)
    resp = await client.patch("/api/notifications/1/read", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["is_read"] is True

    patch_kwargs = patch_db.patch.call_args
    assert patch_kwargs.args[0] == "/notifications/1"
    assert patch_kwargs.kwargs["json"] == {"is_read": True}


# --- push subscribe ----------------------------------------------------------


async def test_push_subscribe_requires_auth(client):
    resp = await client.post(
        "/api/notifications/push-subscribe",
        json={
            "endpoint": "https://push.example.com/abc",
            "keys": {"p256dh": "p256dh-key", "auth": "auth-key"},
        },
    )
    assert resp.status_code == 401


async def test_push_subscribe_missing_keys_returns_422(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user())
    resp = await client.post(
        "/api/notifications/push-subscribe",
        json={"endpoint": "https://push.example.com/abc"},
        headers=_auth_header(),
    )
    assert resp.status_code == 422


async def test_push_subscribe_empty_endpoint_returns_422(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user())
    resp = await client.post(
        "/api/notifications/push-subscribe",
        json={
            "endpoint": "",
            "keys": {"p256dh": "p256dh-key", "auth": "auth-key"},
        },
        headers=_auth_header(),
    )
    assert resp.status_code == 422


async def test_push_subscribe_success(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user())
    patch_db.post.return_value = {
        "id": 1,
        "user_id": 1,
        "endpoint": "https://push.example.com/abc",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    resp = await client.post(
        "/api/notifications/push-subscribe",
        json={
            "endpoint": "https://push.example.com/abc",
            "keys": {"p256dh": "p256dh-key", "auth": "auth-key"},
        },
        headers=_auth_header(),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["endpoint"] == "https://push.example.com/abc"

    post_kwargs = patch_db.post.call_args
    assert post_kwargs.args[0] == "/push-subscriptions"
    assert post_kwargs.kwargs["json"] == {
        "user_id": 1,
        "endpoint": "https://push.example.com/abc",
        "p256dh": "p256dh-key",
        "auth_key": "auth-key",
    }


# --- test-send -----------------------------------------------------------


async def test_test_send_requires_auth(client):
    resp = await client.post("/api/notifications/test-send")
    assert resp.status_code == 401


async def test_test_send_no_subscriptions_returns_zero_counts(client, patch_db, monkeypatch):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user())
    patch_db.get.return_value = []
    mock_send_push = AsyncMock()
    monkeypatch.setattr(push, "send_push", mock_send_push)

    resp = await client.post("/api/notifications/test-send", headers=_auth_header())

    assert resp.status_code == 200
    assert resp.json() == {"sent": 0, "failed": 0}
    mock_send_push.assert_not_called()

    called_path = patch_db.get.call_args.args[0]
    assert called_path == "/push-subscriptions?user_id=1"


async def test_test_send_success_sends_to_all_subscriptions(client, patch_db, monkeypatch):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user())
    subs = [_subscription(id=1), _subscription(id=2)]
    patch_db.get.return_value = subs
    mock_send_push = AsyncMock(return_value=True)
    monkeypatch.setattr(push, "send_push", mock_send_push)

    resp = await client.post("/api/notifications/test-send", headers=_auth_header())

    assert resp.status_code == 200
    assert resp.json() == {"sent": 2, "failed": 0}
    assert mock_send_push.call_count == 2

    for call in mock_send_push.call_args_list:
        sent_payload = call.args[1]
        assert sent_payload == {
            "title": "Test notification",
            "message": "This is a test push from MedByte notifications service.",
            "url": "/notifications",
            "tag": "test",
        }
    patch_db.delete.assert_not_called()


async def test_test_send_counts_non_stale_failure(client, patch_db, monkeypatch):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user())
    patch_db.get.return_value = [_subscription(id=1)]
    mock_send_push = AsyncMock(return_value=False)
    monkeypatch.setattr(push, "send_push", mock_send_push)

    resp = await client.post("/api/notifications/test-send", headers=_auth_header())

    assert resp.status_code == 200
    assert resp.json() == {"sent": 0, "failed": 1}
    patch_db.delete.assert_not_called()


async def test_test_send_cleans_up_stale_subscription(client, patch_db, monkeypatch):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user())
    patch_db.get.return_value = [_subscription(id=1), _subscription(id=2)]

    async def _send(sub, payload):
        if sub["id"] == 1:
            raise push.StaleSubscription(1)
        return True

    monkeypatch.setattr(push, "send_push", _send)

    resp = await client.post("/api/notifications/test-send", headers=_auth_header())

    assert resp.status_code == 200
    assert resp.json() == {"sent": 1, "failed": 0}
    patch_db.delete.assert_called_once_with("/push-subscriptions/1")
