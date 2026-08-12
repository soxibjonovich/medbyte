from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.asyncio


# --- users -----------------------------------------------------------------


async def test_create_user_success(client):
    resp = await client.post(
        "/users", json={"full_name": "Aziz Karimov", "username": "aziz_k"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "aziz_k"
    assert body["role"] == "patient"


async def test_create_user_duplicate_username_conflicts(client):
    await client.post("/users", json={"full_name": "User A", "username": "dupe"})
    resp = await client.post("/users", json={"full_name": "User B", "username": "dupe"})
    assert resp.status_code == 409


async def test_create_user_duplicate_phone_conflicts(client):
    await client.post("/users", json={"full_name": "User A", "username": "ph_u1", "phone": "+998900000001"})
    resp = await client.post("/users", json={"full_name": "User B", "username": "ph_u2", "phone": "+998900000001"})
    assert resp.status_code == 409


async def test_create_user_duplicate_email_conflicts(client):
    await client.post("/users", json={"full_name": "User A", "username": "em_u1", "email": "x@x.com"})
    resp = await client.post("/users", json={"full_name": "User B", "username": "em_u2", "email": "x@x.com"})
    assert resp.status_code == 409


async def test_get_user_not_found(client):
    resp = await client.get("/users/999")
    assert resp.status_code == 404


async def test_update_user_not_found(client):
    resp = await client.patch("/users/999", json={"full_name": "New"})
    assert resp.status_code == 404


async def test_update_user_conflicting_username(client):
    await client.post("/users", json={"full_name": "User A", "username": "taken"})
    created = await client.post("/users", json={"full_name": "User B", "username": "free"})
    user_id = created.json()["id"]
    resp = await client.patch(f"/users/{user_id}", json={"username": "taken"})
    assert resp.status_code == 409


async def test_delete_user(client):
    created = await client.post("/users", json={"full_name": "User A", "username": "delme"})
    user_id = created.json()["id"]
    resp = await client.delete(f"/users/{user_id}")
    assert resp.status_code == 204
    assert (await client.get(f"/users/{user_id}")).status_code == 404


async def test_internal_lookup_by_username_includes_password_hash(client):
    await client.post(
        "/users",
        json={"full_name": "User A", "username": "secret_u", "password_hash": "hashedvalue"},
    )
    resp = await client.get("/users/by-username/secret_u")
    assert resp.status_code == 200
    assert resp.json()["password_hash"] == "hashedvalue"


# --- appointments ------------------------------------------------------------


async def test_create_appointment_requires_existing_user(client):
    resp = await client.post(
        "/appointments",
        json={"user_id": 999, "scheduled_at": datetime.now(timezone.utc).isoformat()},
    )
    assert resp.status_code == 404


async def test_appointment_lifecycle(client):
    user = (await client.post("/users", json={"full_name": "User A", "username": "apt_u"})).json()
    created = await client.post(
        "/appointments",
        json={"user_id": user["id"], "scheduled_at": datetime.now(timezone.utc).isoformat()},
    )
    assert created.status_code == 201
    appointment_id = created.json()["id"]

    resp = await client.get(f"/appointments/{appointment_id}")
    assert resp.status_code == 200

    updated = await client.patch(f"/appointments/{appointment_id}", json={"status": "completed"})
    assert updated.json()["status"] == "completed"

    deleted = await client.delete(f"/appointments/{appointment_id}")
    assert deleted.status_code == 204
    assert (await client.get(f"/appointments/{appointment_id}")).status_code == 404


# --- hospitals ------------------------------------------------------------


async def test_hospital_lifecycle_with_soft_delete(client):
    created = await client.post(
        "/hospitals",
        json={
            "name": "City Clinic",
            "address": "1 Main St",
            "city": "Tashkent",
            "lat": 41.3,
            "lng": 69.2,
            "phone_numbers": ["+998901111111"],
            "working_hours": {"mon": "9-18"},
        },
    )
    assert created.status_code == 201
    hospital_id = created.json()["id"]

    detail = await client.get(f"/hospitals/{hospital_id}")
    assert detail.status_code == 200
    assert detail.json()["phone_numbers"] == ["+998901111111"]

    deleted = await client.delete(f"/hospitals/{hospital_id}")
    assert deleted.status_code == 204
    assert (await client.get(f"/hospitals/{hospital_id}")).status_code == 404


async def test_hospital_leaderboard_endpoint(client):
    await client.post(
        "/hospitals",
        json={"name": "H1", "address": "x", "city": "C", "lat": 0, "lng": 0},
    )
    resp = await client.get("/hospitals/leaderboard")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["rank"] == 1


# --- doctors ------------------------------------------------------------


async def test_create_doctor_requires_existing_hospital_and_category(client):
    resp = await client.post(
        "/doctors",
        json={"hospital_id": 999, "medical_category_id": 999, "full_name": "Dr. X"},
    )
    assert resp.status_code == 404


async def test_create_doctor_success(client):
    hospital = (
        await client.post("/hospitals", json={"name": "H", "address": "x", "city": "C", "lat": 0, "lng": 0})
    ).json()
    category = (await client.post("/medical-categories", json={"name": "Cardiology"})).json()
    resp = await client.post(
        "/doctors",
        json={
            "hospital_id": hospital["id"],
            "medical_category_id": category["id"],
            "full_name": "Dr. House",
        },
    )
    assert resp.status_code == 201


# --- feedback ------------------------------------------------------------


async def test_create_feedback_requires_existing_user_and_appointment(client):
    resp = await client.post("/feedback", json={"user_id": 999, "appointment_id": 999})
    assert resp.status_code == 404


async def test_feedback_processing_internal_endpoint(client):
    user = (await client.post("/users", json={"full_name": "User A", "username": "fb_api_u"})).json()
    hospital = (
        await client.post(
            "/hospitals", json={"name": "H", "address": "x", "city": "C", "lat": 0, "lng": 0}
        )
    ).json()
    question = (
        await client.post(
            "/questions", json={"hospital_id": hospital["id"], "text": "Cleanliness?"}
        )
    ).json()
    appointment = (
        await client.post(
            "/appointments",
            json={"user_id": user["id"], "scheduled_at": datetime.now(timezone.utc).isoformat()},
        )
    ).json()
    feedback = (
        await client.post(
            "/feedback",
            json={
                "user_id": user["id"],
                "appointment_id": appointment["id"],
                "hospital_id": hospital["id"],
                "answers": [
                    {"question_id": question["id"], "question": question["text"], "rating": 4}
                ],
            },
        )
    ).json()
    assert feedback["answers"][0]["rating"] == 4

    resp = await client.patch(
        f"/feedback/{feedback['id']}/processing",
        json={"transcript": "hello", "sentiment": "positive", "processing_status": "done"},
    )
    assert resp.status_code == 200
    assert resp.json()["processing_status"] == "done"

    transcript = await client.get(f"/feedback/{feedback['id']}/transcript")
    assert transcript.status_code == 200
    assert transcript.json()["transcript"] == "hello"


# --- questions -------------------------------------------------------------


async def test_question_lifecycle(client):
    hospital = (
        await client.post(
            "/hospitals", json={"name": "H", "address": "x", "city": "C", "lat": 0, "lng": 0}
        )
    ).json()
    created = (
        await client.post(
            "/questions", json={"hospital_id": hospital["id"], "text": "Wait time?", "position": 1}
        )
    ).json()
    assert created["position"] == 1

    listed = await client.get(f"/questions?hospital_id={hospital['id']}")
    assert [q["id"] for q in listed.json()] == [created["id"]]

    updated = (
        await client.patch(f"/questions/{created['id']}", json={"is_active": False})
    ).json()
    assert updated["is_active"] is False

    resp = await client.delete(f"/questions/{created['id']}")
    assert resp.status_code == 204
    assert (await client.get(f"/questions/{created['id']}")).status_code == 404


# --- payments ------------------------------------------------------------


async def test_create_payment_requires_existing_user_and_appointment(client):
    resp = await client.post(
        "/payments",
        json={"user_id": 999, "appointment_id": 999, "provider": "stripe", "amount": 100},
    )
    assert resp.status_code == 404


async def test_payment_lifecycle(client):
    user = (await client.post("/users", json={"full_name": "User A", "username": "pay_api_u"})).json()
    appointment = (
        await client.post(
            "/appointments",
            json={"user_id": user["id"], "scheduled_at": datetime.now(timezone.utc).isoformat()},
        )
    ).json()
    payment = (
        await client.post(
            "/payments",
            json={
                "user_id": user["id"],
                "appointment_id": appointment["id"],
                "provider": "stripe",
                "amount": 1500,
            },
        )
    ).json()
    assert payment["status"] == "pending"

    updated = await client.patch(
        f"/payments/{payment['id']}", json={"status": "paid", "external_id": "pi_abc"}
    )
    assert updated.json()["status"] == "paid"

    by_external = await client.get("/payments/by-external/pi_abc")
    assert by_external.status_code == 200
    assert by_external.json()["id"] == payment["id"]


# --- stats ------------------------------------------------------------


async def test_stats_overview_endpoint(client):
    resp = await client.get("/stats/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"users_count", "appointments_count", "feedback_count", "revenue"}


async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
