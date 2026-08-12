import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import jwt
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from admin import database_client, security
from admin.main import ConnectionManager, app


def _make_token(user_id: int, expired: bool = False) -> str:
    delta = timedelta(minutes=-5) if expired else timedelta(minutes=60)
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + delta}
    return jwt.encode(payload, security.JWT_SECRET, algorithm=security.JWT_ALGORITHM)


def _user(**overrides):
    record = {"id": 1, "role": "patient"}
    record.update(overrides)
    return record


@pytest.fixture
def patch_get_or_none(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(database_client, "get_or_none", mock)
    return mock


def test_ws_rejects_missing_token():
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/queue/ws"):
            pass
    assert exc_info.value.code == 4401


def test_ws_rejects_invalid_token():
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/queue/ws?token=not-a-real-token"):
            pass
    assert exc_info.value.code == 4401


def test_ws_rejects_non_staff_role(patch_get_or_none):
    patch_get_or_none.return_value = _user(role="patient")
    token = _make_token(1)
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/queue/ws?token={token}"):
            pass
    assert exc_info.value.code == 4403


def test_ws_accepts_staff_role(patch_get_or_none):
    patch_get_or_none.return_value = _user(role="staff")
    token = _make_token(1)
    client = TestClient(app)
    # entering the context manager already proves the handshake succeeded (accept()
    # was called) — _raise_on_close would fire here otherwise. Exiting closes cleanly.
    with client.websocket_connect(f"/api/queue/ws?token={token}"):
        pass


def test_ws_accepts_admin_role(patch_get_or_none):
    patch_get_or_none.return_value = _user(role="admin")
    token = _make_token(1)
    client = TestClient(app)
    with client.websocket_connect(f"/api/queue/ws?token={token}"):
        pass


# --- ConnectionManager.broadcast (isolated, no real RabbitMQ) --------------


class _FakeWebSocket:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.sent: list[dict] = []

    async def send_json(self, message: dict) -> None:
        if self.fail:
            raise RuntimeError("connection dropped")
        self.sent.append(message)


def test_connection_manager_broadcasts_to_all_connections():
    manager = ConnectionManager()
    ws1, ws2 = _FakeWebSocket(), _FakeWebSocket()
    manager.connect(ws1)
    manager.connect(ws2)

    asyncio.run(manager.broadcast({"type": "queue_entry_created", "entry": {"id": 1}}))

    assert ws1.sent == [{"type": "queue_entry_created", "entry": {"id": 1}}]
    assert ws2.sent == [{"type": "queue_entry_created", "entry": {"id": 1}}]


def test_connection_manager_drops_dead_connections_without_crashing():
    manager = ConnectionManager()
    good, bad = _FakeWebSocket(), _FakeWebSocket(fail=True)
    manager.connect(good)
    manager.connect(bad)

    asyncio.run(manager.broadcast({"type": "ping"}))

    assert good.sent == [{"type": "ping"}]
    assert bad not in manager._connections
    assert good in manager._connections
