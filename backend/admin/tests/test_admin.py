from datetime import datetime, timedelta, timezone

import jwt
import pytest

from admin import security

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


def _get_or_none_router(user=None):
    async def _dispatch(path):
        if path.startswith("/users/"):
            return user
        return None

    return _dispatch


async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- auth gating (shared shape across routers) -----------------------------


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/hospitals"),
        ("GET", "/api/doctors"),
        ("GET", "/api/categories"),
        ("GET", "/api/discounts"),
        ("GET", "/api/queue"),
        ("GET", "/api/admin/questions?hospital_id=1"),
        ("GET", "/api/admin/stats/overview"),
        ("GET", "/api/admin/audit-log"),
    ],
)
async def test_requires_auth(client, method, path):
    resp = await client.request(method, path)
    assert resp.status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        "/api/hospitals",
        "/api/doctors",
        "/api/categories",
        "/api/discounts",
        "/api/admin/stats/overview",
        "/api/admin/audit-log",
    ],
)
async def test_admin_only_routes_reject_staff(client, patch_db, path):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="staff"))
    resp = await client.get(path, headers=_auth_header())
    assert resp.status_code == 403


@pytest.mark.parametrize("path", ["/api/queue", "/api/admin/questions?hospital_id=1"])
async def test_staff_only_routes_reject_patient(client, patch_db, path):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="patient"))
    resp = await client.get(path, headers=_auth_header())
    assert resp.status_code == 403


@pytest.mark.parametrize("path", ["/api/queue", "/api/admin/questions?hospital_id=1"])
async def test_staff_only_routes_allow_admin(client, patch_db, path):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="admin"))
    patch_db.get.return_value = []
    resp = await client.get(path, headers=_auth_header())
    assert resp.status_code == 200


# --- hospitals ---------------------------------------------------------


def _hospital(**overrides):
    record = {
        "id": 1,
        "name": "General",
        "address": "1 Main St",
        "city": "Springfield",
        "lat": 1.0,
        "lng": 2.0,
        "rating_avg": 4.5,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    record.update(overrides)
    return record


async def test_list_hospitals_calls_database_client(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="admin"))
    patch_db.get.return_value = [_hospital()]
    resp = await client.get("/api/hospitals?city=Springfield", headers=_auth_header())
    assert resp.status_code == 200
    called_path = patch_db.get.call_args.args[0]
    assert called_path.startswith("/hospitals?")
    assert "city=Springfield" in called_path


async def test_create_hospital_success(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="admin"))
    patch_db.post.return_value = _hospital()
    resp = await client.post(
        "/api/hospitals",
        json={
            "name": "General",
            "address": "1 Main St",
            "city": "Springfield",
            "lat": 1.0,
            "lng": 2.0,
        },
        headers=_auth_header(),
    )
    assert resp.status_code == 201
    assert patch_db.post.call_args_list[0].args[0] == "/hospitals"
    patch_db.post.assert_awaited()


# --- queue --------------------------------------------------------------


def _queue_entry(**overrides):
    record = {
        "id": 5,
        "user_id": 1,
        "hospital_id": 2,
        "doctor_id": None,
        "queue_number": 3,
        "status": "scheduled",
        "scheduled_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    record.update(overrides)
    return record


async def test_list_queue_calls_database_client(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="staff"))
    patch_db.get.return_value = [_queue_entry()]
    resp = await client.get("/api/queue?hospital_id=2", headers=_auth_header())
    assert resp.status_code == 200
    called_path = patch_db.get.call_args.args[0]
    assert called_path.startswith("/appointments?")
    assert "hospital_id=2" in called_path


async def test_create_queue_entry_success_publishes_both_events(client, patch_db, patch_rabbitmq):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="staff"))
    entry = _queue_entry()
    patch_db.post.return_value = entry

    resp = await client.post(
        "/api/queue",
        json={
            "user_id": 1,
            "hospital_id": 2,
            "doctor_id": None,
            "queue_number": 3,
            "scheduled_at": entry["scheduled_at"],
        },
        headers=_auth_header(),
    )

    assert resp.status_code == 201
    assert patch_db.post.call_args_list[0].args[0] == "/appointments"

    patch_rabbitmq.publish_feedback_request.assert_awaited_once()
    feedback_kwargs = patch_rabbitmq.publish_feedback_request.call_args.kwargs
    assert feedback_kwargs["appointment_id"] == entry["id"]
    assert feedback_kwargs["user_id"] == entry["user_id"]

    patch_rabbitmq.publish_queue_update.assert_awaited_once()
    update_call = patch_rabbitmq.publish_queue_update.call_args
    published_event = update_call.args[0] if update_call.args else update_call.kwargs["event"]
    assert published_event == {"type": "queue_entry_created", "entry": entry}

    # audit log entry too
    audit_call = patch_db.post.call_args_list[-1]
    assert audit_call.args[0] == "/audit-log"


async def test_create_queue_entry_succeeds_even_if_publish_queue_update_raises(
    client, patch_db, patch_rabbitmq
):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="staff"))
    entry = _queue_entry()
    patch_db.post.return_value = entry
    patch_rabbitmq.publish_queue_update.side_effect = RuntimeError("rabbitmq down")

    resp = await client.post(
        "/api/queue",
        json={
            "user_id": 1,
            "hospital_id": 2,
            "queue_number": 3,
            "scheduled_at": entry["scheduled_at"],
        },
        headers=_auth_header(),
    )

    assert resp.status_code == 201
    patch_rabbitmq.publish_queue_update.assert_awaited_once()


async def test_create_queue_entry_succeeds_even_if_publish_feedback_request_raises(
    client, patch_db, patch_rabbitmq
):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="staff"))
    entry = _queue_entry()
    patch_db.post.return_value = entry
    patch_rabbitmq.publish_feedback_request.side_effect = RuntimeError("rabbitmq down")

    resp = await client.post(
        "/api/queue",
        json={
            "user_id": 1,
            "hospital_id": 2,
            "queue_number": 3,
            "scheduled_at": entry["scheduled_at"],
        },
        headers=_auth_header(),
    )

    assert resp.status_code == 201
    patch_rabbitmq.publish_queue_update.assert_awaited_once()


# --- questions ------------------------------------------------------------


async def test_create_question_requires_staff(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="patient"))
    resp = await client.post(
        "/api/admin/questions",
        json={"hospital_id": 1, "text": "How was your visit?"},
        headers=_auth_header(),
    )
    assert resp.status_code == 403


async def test_create_question_success(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="staff"))
    patch_db.post.return_value = {
        "id": 1,
        "hospital_id": 1,
        "text": "How was your visit?",
        "position": 0,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    resp = await client.post(
        "/api/admin/questions",
        json={"hospital_id": 1, "text": "How was your visit?"},
        headers=_auth_header(),
    )
    assert resp.status_code == 201
    assert patch_db.post.call_args_list[0].args[0] == "/questions"


# --- stats / audit log ------------------------------------------------


async def test_stats_overview_admin_only_success(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="admin"))
    patch_db.get.return_value = {
        "users_count": 1,
        "appointments_count": 2,
        "feedback_count": 3,
        "revenue": 4.5,
    }
    resp = await client.get("/api/admin/stats/overview", headers=_auth_header())
    assert resp.status_code == 200
    assert patch_db.get.call_args.args[0] == "/stats/overview"


async def test_audit_log_admin_only_success(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="admin"))
    patch_db.get.return_value = []
    resp = await client.get("/api/admin/audit-log", headers=_auth_header())
    assert resp.status_code == 200
    called_path = patch_db.get.call_args.args[0]
    assert called_path.startswith("/audit-log?")
