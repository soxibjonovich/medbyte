from datetime import datetime, timedelta, timezone

import pytest

from database import crud
from database.models import (
    AppointmentStatus,
    FeedbackProcessingStatus,
    FeedbackSentiment,
    PaymentProvider,
    PaymentStatus,
    UserRole,
)

pytestmark = pytest.mark.asyncio


# --- users -----------------------------------------------------------------


async def test_create_and_get_user(session):
    user = await crud.create_user(session, full_name="Aziz Karimov", username="aziz_k")
    fetched = await crud.get_user(session, user.id)
    assert fetched is not None
    assert fetched.username == "aziz_k"
    assert fetched.role == UserRole.patient


async def test_get_user_missing_returns_none(session):
    assert await crud.get_user(session, 999) is None


async def test_get_user_by_username_phone_email(session):
    await crud.create_user(
        session, full_name="A", username="u1", phone="+998900000000", email="a@x.com"
    )
    assert (await crud.get_user_by_username(session, "u1")) is not None
    assert (await crud.get_user_by_phone(session, "+998900000000")) is not None
    assert (await crud.get_user_by_email(session, "a@x.com")) is not None
    assert (await crud.get_user_by_username(session, "nope")) is None


async def test_update_user_partial(session):
    user = await crud.create_user(session, full_name="Old Name", username="u2")
    updated = await crud.update_user(session, user, full_name="New Name")
    assert updated.full_name == "New Name"
    assert updated.username == "u2"


async def test_update_user_role(session):
    user = await crud.create_user(session, full_name="A", username="u3")
    updated = await crud.update_user(session, user, role=UserRole.staff)
    assert updated.role == UserRole.staff


async def test_delete_user(session):
    user = await crud.create_user(session, full_name="A", username="u4")
    await crud.delete_user(session, user)
    assert await crud.get_user(session, user.id) is None


async def test_list_users_pagination(session):
    for i in range(5):
        await crud.create_user(session, full_name=f"U{i}", username=f"user{i}")
    page1 = await crud.list_users(session, limit=2, offset=0)
    page2 = await crud.list_users(session, limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0].id != page2[0].id


# --- appointments ------------------------------------------------------------


async def _make_user(session, **kw):
    kw.setdefault("full_name", "Test User")
    kw.setdefault("username", f"u_{id(kw)}")
    return await crud.create_user(session, **kw)


async def test_create_appointment_and_get(session):
    user = await crud.create_user(session, full_name="A", username="apt_u")
    appointment = await crud.create_appointment(
        session, user_id=user.id, scheduled_at=datetime.now(timezone.utc)
    )
    fetched = await crud.get_appointment(session, appointment.id)
    assert fetched is not None
    assert fetched.status == AppointmentStatus.scheduled


async def test_list_appointments_filtered_by_user(session):
    u1 = await crud.create_user(session, full_name="A", username="apt_u1")
    u2 = await crud.create_user(session, full_name="B", username="apt_u2")
    now = datetime.now(timezone.utc)
    await crud.create_appointment(session, user_id=u1.id, scheduled_at=now)
    await crud.create_appointment(session, user_id=u2.id, scheduled_at=now)
    only_u1 = await crud.list_appointments(session, user_id=u1.id)
    assert len(only_u1) == 1
    assert only_u1[0].user_id == u1.id


async def test_update_appointment_status(session):
    user = await crud.create_user(session, full_name="A", username="apt_u3")
    appointment = await crud.create_appointment(
        session, user_id=user.id, scheduled_at=datetime.now(timezone.utc)
    )
    updated = await crud.update_appointment(
        session, appointment, status_=AppointmentStatus.completed
    )
    assert updated.status == AppointmentStatus.completed


async def test_delete_appointment(session):
    user = await crud.create_user(session, full_name="A", username="apt_u4")
    appointment = await crud.create_appointment(
        session, user_id=user.id, scheduled_at=datetime.now(timezone.utc)
    )
    await crud.delete_appointment(session, appointment)
    assert await crud.get_appointment(session, appointment.id) is None


# --- notifications -----------------------------------------------------------


async def test_create_list_update_delete_notification(session):
    user = await crud.create_user(session, full_name="A", username="notif_u")
    notif = await crud.create_notification(session, user_id=user.id, title="Hi", message="Hello")
    assert notif.is_read is False

    listed = await crud.list_notifications(session, user_id=user.id)
    assert len(listed) == 1

    updated = await crud.update_notification(session, notif, is_read=True)
    assert updated.is_read is True

    await crud.delete_notification(session, notif)
    assert await crud.get_notification(session, notif.id) is None


# --- questions -----------------------------------------------------------


async def test_question_crud(session):
    hospital = await crud.create_hospital(session, name="H", address="x", city="C", lat=0, lng=0)
    q1 = await crud.create_question(session, hospital_id=hospital.id, text="Cleanliness?", position=0)
    q2 = await crud.create_question(session, hospital_id=hospital.id, text="Wait time?", position=1)
    assert q1.is_active is True

    listed = await crud.list_questions(session, hospital_id=hospital.id)
    assert [q.id for q in listed] == [q1.id, q2.id]

    updated = await crud.update_question(session, q2, is_active=False)
    assert updated.is_active is False

    await crud.delete_question(session, q1)
    assert await crud.get_question(session, q1.id) is None
    assert len(await crud.list_questions(session, hospital_id=hospital.id)) == 1


# --- payments ------------------------------------------------------------


async def test_create_payment_and_lookup_by_external_id(session):
    user = await crud.create_user(session, full_name="A", username="pay_u")
    appointment = await crud.create_appointment(
        session, user_id=user.id, scheduled_at=datetime.now(timezone.utc)
    )
    payment = await crud.create_payment(
        session,
        user_id=user.id,
        appointment_id=appointment.id,
        provider=PaymentProvider.stripe,
        amount=1000,
        currency="usd",
    )
    assert payment.status == PaymentStatus.pending

    updated = await crud.update_payment(
        session, payment, external_id="pi_123", status_=PaymentStatus.paid
    )
    assert updated.external_id == "pi_123"
    assert updated.status == PaymentStatus.paid

    fetched = await crud.get_payment_by_external_id(session, "pi_123")
    assert fetched is not None
    assert fetched.id == payment.id


# --- discounts ------------------------------------------------------------


async def test_discount_lifecycle(session):
    user = await crud.create_user(session, full_name="A", username="disc_u")
    discount = await crud.create_discount(
        session, user_id=user.id, title="10% off", code="SAVE10", percent_off=10
    )
    assert discount.is_used is False

    listed = await crud.list_discounts(session, user_id=user.id)
    assert len(listed) == 1

    updated = await crud.update_discount(session, discount, is_used=True)
    assert updated.is_used is True

    await crud.delete_discount(session, discount)
    assert await crud.get_discount(session, discount.id) is None


# --- hospitals / doctors / categories --------------------------------------


async def test_create_hospital_with_array_and_jsonb_fields(session):
    hospital = await crud.create_hospital(
        session,
        name="City Clinic",
        address="1 Main St",
        city="Tashkent",
        lat=41.3,
        lng=69.2,
        phone_numbers=["+998901111111", "+998902222222"],
        working_hours={"mon": "9-18"},
    )
    fetched = await crud.get_hospital(session, hospital.id)
    assert fetched.phone_numbers == ["+998901111111", "+998902222222"]
    assert fetched.working_hours == {"mon": "9-18"}


async def test_soft_delete_hospital_excluded_from_get_and_list(session):
    hospital = await crud.create_hospital(
        session, name="Old Clinic", address="A", city="Tashkent", lat=0, lng=0
    )
    await crud.soft_delete_hospital(session, hospital)
    assert await crud.get_hospital(session, hospital.id) is None
    listed = await crud.list_hospitals(session)
    assert hospital.id not in [h.id for h in listed]


async def test_list_hospitals_filter_by_city(session):
    await crud.create_hospital(session, name="A", address="x", city="Tashkent", lat=0, lng=0)
    await crud.create_hospital(session, name="B", address="x", city="Samarkand", lat=0, lng=0)
    tashkent_only = await crud.list_hospitals(session, city="Tashkent")
    assert len(tashkent_only) == 1
    assert tashkent_only[0].city == "Tashkent"


async def test_list_hospitals_sort_by_distance(session):
    near = await crud.create_hospital(session, name="Near", address="x", city="C", lat=41.30, lng=69.25)
    far = await crud.create_hospital(session, name="Far", address="x", city="C", lat=50.0, lng=80.0)
    ranked = await crud.list_hospitals(session, sort="distance", lat=41.30, lng=69.25)
    assert ranked[0].id == near.id
    assert ranked[-1].id == far.id


async def test_list_hospitals_sort_by_rating(session):
    await crud.create_hospital(session, name="Low", address="x", city="C", lat=0, lng=0)
    high = await crud.create_hospital(session, name="High", address="x", city="C", lat=0, lng=0)
    high.rating_avg = 4.9
    await session.commit()
    ranked = await crud.list_hospitals(session, sort="rating")
    assert ranked[0].id == high.id


async def test_hospital_leaderboard_weighting(session):
    hospital = await crud.create_hospital(session, name="H", address="x", city="C", lat=0, lng=0)
    hospital.rating_avg = 4.0
    await session.commit()
    user = await crud.create_user(session, full_name="A", username="lb_u")
    for _ in range(3):
        await crud.create_appointment(
            session, user_id=user.id, hospital_id=hospital.id, scheduled_at=datetime.now(timezone.utc)
        )
    ranked = await crud.list_hospital_leaderboard(session)
    assert ranked[0][0].id == hospital.id
    # weighted_score = rating*0.7 + min(count,100)/100*5*0.3
    expected = round(4.0 * 0.7 + min(3, 100) / 100 * 5 * 0.3, 2)
    assert ranked[0][1] == expected


async def test_doctor_and_medical_category_lifecycle(session):
    category = await crud.create_medical_category(session, name="Cardiology")
    hospital = await crud.create_hospital(session, name="H", address="x", city="C", lat=0, lng=0)
    doctor = await crud.create_doctor(
        session,
        hospital_id=hospital.id,
        medical_category_id=category.id,
        full_name="Dr. House",
        experience_years=10,
    )
    fetched = await crud.get_doctor(session, doctor.id)
    assert fetched.full_name == "Dr. House"

    by_hospital = await crud.list_doctors_by_hospital(session, hospital.id)
    assert len(by_hospital) == 1

    updated = await crud.update_doctor(session, doctor, experience_years=11)
    assert updated.experience_years == 11

    await crud.delete_doctor(session, doctor)
    assert await crud.get_doctor(session, doctor.id) is None

    updated_cat = await crud.update_medical_category(session, category, name="Neurology")
    assert updated_cat.name == "Neurology"
    await crud.delete_medical_category(session, category)
    assert await crud.get_medical_category(session, category.id) is None


async def test_list_doctors_filters(session):
    cat1 = await crud.create_medical_category(session, name="Cardiology")
    cat2 = await crud.create_medical_category(session, name="Neurology")
    hospital = await crud.create_hospital(session, name="H", address="x", city="C", lat=0, lng=0)
    await crud.create_doctor(session, hospital_id=hospital.id, medical_category_id=cat1.id, full_name="D1")
    await crud.create_doctor(session, hospital_id=hospital.id, medical_category_id=cat2.id, full_name="D2")
    cat1_only = await crud.list_doctors(session, category_id=cat1.id)
    assert len(cat1_only) == 1
    assert cat1_only[0].full_name == "D1"


# --- feedback ------------------------------------------------------------


async def test_create_feedback_and_get(session):
    user = await crud.create_user(session, full_name="A", username="fb_u")
    hospital = await crud.create_hospital(session, name="H", address="x", city="C", lat=0, lng=0)
    question = await crud.create_question(session, hospital_id=hospital.id, text="Cleanliness?")
    appointment = await crud.create_appointment(
        session, user_id=user.id, scheduled_at=datetime.now(timezone.utc)
    )
    answers = [
        {"question_id": question.id, "question": question.text, "rating": 5, "comment": "spotless"}
    ]
    feedback = await crud.create_feedback(
        session, user_id=user.id, appointment_id=appointment.id, answers=answers
    )
    assert feedback.processing_status == FeedbackProcessingStatus.pending
    assert feedback.answers == answers

    fetched = await crud.get_feedback(session, feedback.id)
    assert fetched.answers[0]["rating"] == 5


async def test_update_feedback_processing(session):
    user = await crud.create_user(session, full_name="A", username="fb_u2")
    appointment = await crud.create_appointment(
        session, user_id=user.id, scheduled_at=datetime.now(timezone.utc)
    )
    feedback = await crud.create_feedback(
        session, user_id=user.id, appointment_id=appointment.id
    )
    updated = await crud.update_feedback_processing(
        session,
        feedback,
        transcript="great service",
        sentiment=FeedbackSentiment.positive,
        keywords=["service"],
        processing_status=FeedbackProcessingStatus.done,
    )
    assert updated.transcript == "great service"
    assert updated.sentiment == FeedbackSentiment.positive
    assert updated.keywords == ["service"]
    assert updated.processing_status == FeedbackProcessingStatus.done


async def test_list_feedback_filters(session):
    user = await crud.create_user(session, full_name="A", username="fb_u3")
    appointment = await crud.create_appointment(
        session, user_id=user.id, scheduled_at=datetime.now(timezone.utc)
    )
    fb1 = await crud.create_feedback(session, user_id=user.id, appointment_id=appointment.id)
    await crud.update_feedback_processing(session, fb1, sentiment=FeedbackSentiment.positive)
    fb2 = await crud.create_feedback(session, user_id=user.id, appointment_id=appointment.id)
    await crud.update_feedback_processing(session, fb2, sentiment=FeedbackSentiment.negative)

    positive_only = await crud.list_feedback(session, sentiment=FeedbackSentiment.positive)
    assert [f.id for f in positive_only] == [fb1.id]


async def test_list_feedback_date_range(session):
    user = await crud.create_user(session, full_name="A", username="fb_u4")
    appointment = await crud.create_appointment(
        session, user_id=user.id, scheduled_at=datetime.now(timezone.utc)
    )
    await crud.create_feedback(session, user_id=user.id, appointment_id=appointment.id)
    future = datetime.now(timezone.utc) + timedelta(days=1)
    none_found = await crud.list_feedback(session, date_from=future)
    assert none_found == []


# --- audit log & stats --------------------------------------------------


async def test_audit_log_create_and_list(session):
    user = await crud.create_user(session, full_name="A", username="audit_u")
    entry = await crud.create_audit_log(
        session, actor_id=user.id, action="delete", entity="hospital", entity_id=1
    )
    listed = await crud.list_audit_log(session)
    assert entry.id in [e.id for e in listed]


async def test_stats_overview(session):
    user = await crud.create_user(session, full_name="A", username="stats_u")
    appointment = await crud.create_appointment(
        session, user_id=user.id, scheduled_at=datetime.now(timezone.utc)
    )
    await crud.create_feedback(session, user_id=user.id, appointment_id=appointment.id)
    await crud.create_discount(
        session, user_id=user.id, title="t", code="c", percent_off=10
    )
    discount2 = await crud.create_discount(
        session, user_id=user.id, title="t2", code="c2", percent_off=20
    )
    await crud.update_discount(session, discount2, is_used=True)

    stats = await crud.get_stats_overview(session)
    assert stats["users_count"] == 1
    assert stats["appointments_count"] == 1
    assert stats["feedback_count"] == 1
    assert stats["revenue"] == 1.0


async def test_visits_by_category(session):
    category = await crud.create_medical_category(session, name="Cardiology")
    hospital = await crud.create_hospital(session, name="H", address="x", city="C", lat=0, lng=0)
    doctor = await crud.create_doctor(
        session, hospital_id=hospital.id, medical_category_id=category.id, full_name="Dr. X"
    )
    user = await crud.create_user(session, full_name="A", username="visits_u")
    await crud.create_appointment(
        session, user_id=user.id, doctor_id=doctor.id, scheduled_at=datetime.now(timezone.utc)
    )
    rows = await crud.get_visits_by_category(session)
    assert rows == [(category.id, "Cardiology", 1)]
