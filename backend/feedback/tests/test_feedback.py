from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import jwt
import pytest

from feedback import rate_limit, security

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


def _appointment(**overrides):
    record = {
        "id": 1,
        "user_id": 1,
        "hospital_id": 2,
        "doctor_id": None,
    }
    record.update(overrides)
    return record


def _get_or_none_router(user=None, appointment=None, doctor=None, questions=None, feedback=None):
    async def _dispatch(path):
        if path.startswith("/users/"):
            return user
        if path.startswith("/appointments/"):
            return appointment
        if path.startswith("/doctors/"):
            return doctor
        if path.startswith("/questions"):
            return questions
        if "/transcript" in path:
            return feedback
        if path.startswith("/feedback/"):
            return feedback
        return None

    return _dispatch


def _ratings(**overrides):
    record = {
        "professionalism": 4,
        "communication": 5,
        "punctuality": 4,
        "attentiveness": 5,
        "effectiveness": 4,
    }
    record.update(overrides)
    return record


def _ratings_data(**overrides):
    return {key: str(value) for key, value in _ratings(**overrides).items()}


async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- create feedback --------------------------------------------------


async def test_create_feedback_requires_auth(client):
    resp = await client.post("/api/feedback", data={"appointment_id": "1"})
    assert resp.status_code == 401


async def test_create_feedback_appointment_not_found(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(), appointment=None)
    resp = await client.post(
        "/api/feedback", data={**_ratings_data(), "appointment_id": "1"}, headers=_auth_header()
    )
    assert resp.status_code == 404


async def test_create_feedback_not_your_appointment(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(), appointment=_appointment(user_id=999)
    )
    resp = await client.post(
        "/api/feedback", data={**_ratings_data(), "appointment_id": "1"}, headers=_auth_header()
    )
    assert resp.status_code == 403


async def test_create_feedback_missing_characteristic_rating(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(), appointment=_appointment(hospital_id=None)
    )
    resp = await client.post(
        "/api/feedback",
        data={
            "appointment_id": "1",
            "professionalism": "4",
            "communication": "5",
            "punctuality": "4",
            "attentiveness": "5",
        },
        headers=_auth_header(),
    )
    assert resp.status_code == 422


async def test_create_feedback_characteristic_rating_out_of_range(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(), appointment=_appointment(hospital_id=None)
    )
    resp = await client.post(
        "/api/feedback",
        data={
            "appointment_id": "1",
            "professionalism": "4",
            "communication": "6",
            "punctuality": "4",
            "attentiveness": "5",
            "effectiveness": "5",
        },
        headers=_auth_header(),
    )
    assert resp.status_code == 422
    assert "communication" in resp.json()["detail"]


async def test_create_feedback_rate_limited_returns_429(client, patch_db, monkeypatch):
    """Wiring check only: verifies the "create_feedback" bucket dependency raises
    429 when is_allowed() reports the caller is over the limit. Doesn't need
    real Redis — the module-level `is_allowed` is mocked directly."""
    mock_allowed = AsyncMock(return_value=False)
    monkeypatch.setattr(rate_limit, "is_allowed", mock_allowed)
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user())

    resp = await client.post(
        "/api/feedback", data={"appointment_id": "1"}, headers=_auth_header()
    )
    assert resp.status_code == 429
    assert resp.headers["retry-after"] == "60"
    mock_allowed.assert_awaited_once_with("create_feedback", "127.0.0.1", 20, 60)


async def test_create_feedback_success_no_audio(client, patch_db, patch_rabbitmq):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(),
        appointment=_appointment(hospital_id=2, doctor_id=None),
    )
    patch_db.post.return_value = {
        "id": 10,
        "user_id": 1,
        "appointment_id": 1,
        "hospital_id": 2,
        "doctor_id": None,
        "category_id": None,
        "rating": 4.4,
        "tags": ["Friendly doctor"],
        "text_comment": "Great visit",
        "answers": [
            {"question_id": 1, "question": "Professionalism", "rating": 4, "comment": None},
            {"question_id": 2, "question": "Communication", "rating": 5, "comment": None},
            {"question_id": 3, "question": "Punctuality", "rating": 4, "comment": None},
            {"question_id": 4, "question": "Attentiveness", "rating": 5, "comment": None},
            {"question_id": 5, "question": "Effectiveness", "rating": 4, "comment": None},
            {"question_id": 0, "question": "Additional comments", "rating": None, "comment": "Great visit"},
            {"question_id": -1, "question": "What they liked", "rating": None, "comment": "Friendly doctor"},
        ],
        "audio_file": None,
        "transcript": None,
        "sentiment": None,
        "processing_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    resp = await client.post(
        "/api/feedback",
        data={**_ratings_data(), "appointment_id": "1", "text_comment": "Great visit", "tags": "Friendly doctor"},
        headers=_auth_header(),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 10
    assert body["rating"] == 4.4
    assert body["answers"][0]["question"] == "Professionalism"

    post_kwargs = patch_db.post.call_args.kwargs
    assert post_kwargs["json"]["rating"] == 4.4
    assert post_kwargs["json"]["tags"] == ["Friendly doctor"]
    assert post_kwargs["json"]["text_comment"] == "Great visit"
    assert len(post_kwargs["json"]["answers"]) == 7
    assert post_kwargs["json"]["audio_file"] is None
    patch_rabbitmq.assert_not_called()


async def test_create_feedback_averages_five_ratings(client, patch_db, patch_rabbitmq):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(), appointment=_appointment(hospital_id=None, doctor_id=None)
    )
    patch_db.post.return_value = {
        "id": 13,
        "user_id": 1,
        "appointment_id": 1,
        "hospital_id": None,
        "doctor_id": None,
        "category_id": None,
        "rating": 4.0,
        "tags": [],
        "text_comment": None,
        "answers": [],
        "audio_file": None,
        "transcript": None,
        "sentiment": None,
        "processing_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    resp = await client.post(
        "/api/feedback",
        data={**_ratings_data(), "appointment_id": "1"},
        headers=_auth_header(),
    )
    assert resp.status_code == 201

    post_kwargs = patch_db.post.call_args.kwargs
    # (4 + 5 + 4 + 5 + 4) / 5 == 4.4
    assert post_kwargs["json"]["rating"] == 4.4
    assert [answer["rating"] for answer in post_kwargs["json"]["answers"][:5]] == [4, 5, 4, 5, 4]


async def test_create_feedback_category_id_derived_from_doctor(client, patch_db, patch_rabbitmq):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(),
        appointment=_appointment(hospital_id=None, doctor_id=7),
        doctor={"id": 7, "medical_category_id": 42},
    )
    patch_db.post.return_value = {
        "id": 11,
        "user_id": 1,
        "appointment_id": 1,
        "hospital_id": None,
        "doctor_id": 7,
        "category_id": 42,
        "rating": 4.0,
        "tags": [],
        "text_comment": None,
        "answers": [],
        "audio_file": None,
        "transcript": None,
        "sentiment": None,
        "processing_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    resp = await client.post(
        "/api/feedback", data={**_ratings_data(), "appointment_id": "1"}, headers=_auth_header()
    )
    assert resp.status_code == 201
    post_kwargs = patch_db.post.call_args.kwargs
    assert post_kwargs["json"]["category_id"] == 42
    patch_rabbitmq.assert_not_called()


async def test_create_feedback_with_audio_publishes_stt_job(client, patch_db, patch_rabbitmq):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(), appointment=_appointment(hospital_id=None, doctor_id=None)
    )
    patch_db.post.return_value = {
        "id": 12,
        "user_id": 1,
        "appointment_id": 1,
        "hospital_id": None,
        "doctor_id": None,
        "category_id": None,
        "rating": 4.0,
        "tags": [],
        "text_comment": None,
        "answers": [],
        "audio_file": "audio_uploads/fake.wav",
        "transcript": None,
        "sentiment": None,
        "processing_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    resp = await client.post(
        "/api/feedback",
        data={**_ratings_data(), "appointment_id": "1"},
        files={"audio_file": ("note.wav", b"fake audio bytes", "audio/wav")},
        headers=_auth_header(),
    )
    assert resp.status_code == 201
    patch_rabbitmq.assert_called_once()
    call_args = patch_rabbitmq.call_args
    assert call_args.args[0] == 12


# --- questions ----------------------------------------------------------


async def test_get_appointment_questions_requires_auth(client):
    resp = await client.get("/api/feedback/questions/1")
    assert resp.status_code == 401


async def test_get_appointment_questions_not_found(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(), appointment=None)
    resp = await client.get("/api/feedback/questions/1", headers=_auth_header())
    assert resp.status_code == 404


async def test_get_appointment_questions_forbidden(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(), appointment=_appointment(user_id=999)
    )
    resp = await client.get("/api/feedback/questions/1", headers=_auth_header())
    assert resp.status_code == 403


async def test_get_appointment_questions_no_hospital_returns_empty(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(), appointment=_appointment(hospital_id=None)
    )
    resp = await client.get("/api/feedback/questions/1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_appointment_questions_success(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(),
        appointment=_appointment(hospital_id=2),
        questions=[{"id": 1, "hospital_id": 2, "text": "Q1", "position": 0, "is_active": True}],
    )
    resp = await client.get("/api/feedback/questions/1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()[0]["text"] == "Q1"


# --- get feedback ---------------------------------------------------------


def _feedback(**overrides):
    record = {
        "id": 1,
        "user_id": 1,
        "appointment_id": 1,
        "hospital_id": 2,
        "doctor_id": None,
        "category_id": None,
        "answers": [],
        "audio_file": None,
        "transcript": None,
        "sentiment": None,
        "processing_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    record.update(overrides)
    return record


async def test_get_feedback_requires_auth(client):
    resp = await client.get("/api/feedback/1")
    assert resp.status_code == 401


async def test_get_feedback_not_found(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(), feedback=None)
    resp = await client.get("/api/feedback/1", headers=_auth_header())
    assert resp.status_code == 404


async def test_get_feedback_forbidden_for_other_user(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(), feedback=_feedback(user_id=999)
    )
    resp = await client.get("/api/feedback/1", headers=_auth_header())
    assert resp.status_code == 403


async def test_get_feedback_owner_success(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(), feedback=_feedback(user_id=1)
    )
    resp = await client.get("/api/feedback/1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["id"] == 1


async def test_get_feedback_admin_can_view_others(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(role="admin"), feedback=_feedback(user_id=999)
    )
    resp = await client.get("/api/feedback/1", headers=_auth_header())
    assert resp.status_code == 200


# --- list feedback (admin only) -------------------------------------------


async def test_list_feedback_requires_admin(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="patient"))
    resp = await client.get("/api/feedback", headers=_auth_header())
    assert resp.status_code == 403


async def test_list_feedback_success(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="admin"))
    patch_db.get.return_value = [_feedback()]
    resp = await client.get(
        "/api/feedback?hospital_id=2&sentiment=positive", headers=_auth_header()
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    called_path = patch_db.get.call_args.args[0]
    assert called_path.startswith("/feedback?")
    assert "hospital_id=2" in called_path
    assert "sentiment=positive" in called_path


# --- transcript (admin only) ----------------------------------------------


async def test_get_transcript_requires_admin(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="patient"))
    resp = await client.get("/api/feedback/1/transcript", headers=_auth_header())
    assert resp.status_code == 403


async def test_get_transcript_not_found(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(user=_user(role="admin"), feedback=None)
    resp = await client.get("/api/feedback/1/transcript", headers=_auth_header())
    assert resp.status_code == 404


async def test_get_transcript_success(client, patch_db):
    patch_db.get_or_none.side_effect = _get_or_none_router(
        user=_user(role="admin"),
        feedback={
            "id": 1,
            "transcript": "hello there",
            "sentiment": "positive",
            "keywords": ["hello"],
            "processing_status": "done",
        },
    )
    resp = await client.get("/api/feedback/1/transcript", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["transcript"] == "hello there"
