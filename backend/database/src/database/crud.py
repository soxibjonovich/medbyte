import math
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Appointment,
    AppointmentStatus,
    AuditLog,
    Discount,
    Doctor,
    Feedback,
    FeedbackProcessingStatus,
    FeedbackSentiment,
    Hospital,
    MedicalCategory,
    Notification,
    Payment,
    PaymentProvider,
    PaymentStatus,
    PushSubscription,
    Question,
    User,
    UserRole,
)


async def list_users(session: AsyncSession, limit: int = 50, offset: int = 0) -> list[User]:
    result = await session.execute(select(User).order_by(User.id).limit(limit).offset(offset))
    return list(result.scalars().all())


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_user_by_phone(session: AsyncSession, phone: str) -> User | None:
    result = await session.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    full_name: str,
    username: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    password_hash: str | None = None,
    role: UserRole = UserRole.patient,
) -> User:
    user = User(
        full_name=full_name,
        username=username,
        phone=phone,
        email=email,
        password_hash=password_hash,
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(
    session: AsyncSession,
    user: User,
    full_name: str | None = None,
    username: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    role: UserRole | None = None,
) -> User:
    if full_name is not None:
        user.full_name = full_name
    if username is not None:
        user.username = username
    if phone is not None:
        user.phone = phone
    if email is not None:
        user.email = email
    if role is not None:
        user.role = role

    await session.commit()
    await session.refresh(user)
    return user


async def delete_user(session: AsyncSession, user: User) -> None:
    await session.delete(user)
    await session.commit()


async def list_appointments(
    session: AsyncSession,
    user_id: int | None = None,
    hospital_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Appointment]:
    stmt = select(Appointment).order_by(Appointment.scheduled_at.desc())
    if user_id is not None:
        stmt = stmt.where(Appointment.user_id == user_id)
    if hospital_id is not None:
        stmt = stmt.where(Appointment.hospital_id == hospital_id)
    result = await session.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all())


async def get_appointment(session: AsyncSession, appointment_id: int) -> Appointment | None:
    return await session.get(Appointment, appointment_id)


async def create_appointment(
    session: AsyncSession,
    user_id: int,
    scheduled_at: datetime,
    hospital_id: int | None = None,
    doctor_id: int | None = None,
    queue_number: int | None = None,
    status_: AppointmentStatus = AppointmentStatus.scheduled,
) -> Appointment:
    appointment = Appointment(
        user_id=user_id,
        hospital_id=hospital_id,
        doctor_id=doctor_id,
        queue_number=queue_number,
        status=status_,
        scheduled_at=scheduled_at,
    )
    session.add(appointment)
    await session.commit()
    await session.refresh(appointment)
    return appointment


async def update_appointment(
    session: AsyncSession,
    appointment: Appointment,
    hospital_id: int | None = None,
    doctor_id: int | None = None,
    queue_number: int | None = None,
    status_: AppointmentStatus | None = None,
    scheduled_at: datetime | None = None,
) -> Appointment:
    if hospital_id is not None:
        appointment.hospital_id = hospital_id
    if doctor_id is not None:
        appointment.doctor_id = doctor_id
    if queue_number is not None:
        appointment.queue_number = queue_number
    if status_ is not None:
        appointment.status = status_
    if scheduled_at is not None:
        appointment.scheduled_at = scheduled_at
    await session.commit()
    await session.refresh(appointment)
    return appointment


async def delete_appointment(session: AsyncSession, appointment: Appointment) -> None:
    await session.delete(appointment)
    await session.commit()


async def assign_queue_number(
    session: AsyncSession, appointment: Appointment
) -> Appointment:
    """Assign the next sequential queue number for the hospital on the appointment day.

    Idempotent — returns unchanged appointment if a queue number already exists.
    """
    if appointment.queue_number is not None:
        return appointment
    result = await session.execute(
        select(func.max(Appointment.queue_number)).where(
            Appointment.hospital_id == appointment.hospital_id,
            func.date(Appointment.scheduled_at) == func.date(appointment.scheduled_at),
            Appointment.queue_number.isnot(None),
        )
    )
    current_max = result.scalar_one()
    appointment.queue_number = (current_max or 0) + 1
    await session.commit()
    await session.refresh(appointment)
    return appointment


async def list_notifications(
    session: AsyncSession, user_id: int | None = None, limit: int = 50, offset: int = 0
) -> list[Notification]:
    stmt = select(Notification).order_by(Notification.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(Notification.user_id == user_id)
    result = await session.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all())


async def get_notification(session: AsyncSession, notification_id: int) -> Notification | None:
    return await session.get(Notification, notification_id)


async def create_notification(
    session: AsyncSession, user_id: int, title: str, message: str
) -> Notification:
    notification = Notification(user_id=user_id, title=title, message=message)
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return notification


async def update_notification(
    session: AsyncSession, notification: Notification, is_read: bool | None = None
) -> Notification:
    if is_read is not None:
        notification.is_read = is_read
    await session.commit()
    await session.refresh(notification)
    return notification


async def delete_notification(session: AsyncSession, notification: Notification) -> None:
    await session.delete(notification)
    await session.commit()


async def get_push_subscription_by_endpoint(
    session: AsyncSession, endpoint: str
) -> PushSubscription | None:
    result = await session.execute(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )
    return result.scalar_one_or_none()


async def get_push_subscription_by_id(
    session: AsyncSession, subscription_id: int
) -> PushSubscription | None:
    return await session.get(PushSubscription, subscription_id)


async def list_push_subscriptions(
    session: AsyncSession, user_id: int | None = None, limit: int = 50, offset: int = 0
) -> list[PushSubscription]:
    stmt = select(PushSubscription).order_by(PushSubscription.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(PushSubscription.user_id == user_id)
    result = await session.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all())


async def delete_push_subscription(session: AsyncSession, subscription: PushSubscription) -> None:
    await session.delete(subscription)
    await session.commit()


async def list_questions(
    session: AsyncSession, hospital_id: int | None = None, limit: int = 50, offset: int = 0
) -> list[Question]:
    stmt = select(Question).order_by(Question.position.asc(), Question.id.asc())
    if hospital_id is not None:
        stmt = stmt.where(Question.hospital_id == hospital_id)
    result = await session.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all())


async def get_question(session: AsyncSession, question_id: int) -> Question | None:
    return await session.get(Question, question_id)


async def create_question(
    session: AsyncSession, hospital_id: int, text: str, position: int = 0
) -> Question:
    question = Question(hospital_id=hospital_id, text=text, position=position)
    session.add(question)
    await session.commit()
    await session.refresh(question)
    return question


async def update_question(
    session: AsyncSession,
    question: Question,
    text: str | None = None,
    position: int | None = None,
    is_active: bool | None = None,
) -> Question:
    if text is not None:
        question.text = text
    if position is not None:
        question.position = position
    if is_active is not None:
        question.is_active = is_active
    await session.commit()
    await session.refresh(question)
    return question


async def delete_question(session: AsyncSession, question: Question) -> None:
    await session.delete(question)
    await session.commit()


async def create_push_subscription(
    session: AsyncSession, user_id: int, endpoint: str, p256dh: str, auth_key: str
) -> PushSubscription:
    subscription = PushSubscription(
        user_id=user_id, endpoint=endpoint, p256dh=p256dh, auth_key=auth_key
    )
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def get_payment(session: AsyncSession, payment_id: int) -> Payment | None:
    return await session.get(Payment, payment_id)


async def get_payment_by_external_id(session: AsyncSession, external_id: str) -> Payment | None:
    result = await session.execute(select(Payment).where(Payment.external_id == external_id))
    return result.scalar_one_or_none()


async def create_payment(
    session: AsyncSession,
    user_id: int,
    appointment_id: int,
    provider: PaymentProvider,
    amount: int,
    currency: str,
) -> Payment:
    payment = Payment(
        user_id=user_id,
        appointment_id=appointment_id,
        provider=provider,
        amount=amount,
        currency=currency,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def update_payment(
    session: AsyncSession,
    payment: Payment,
    external_id: str | None = None,
    status_: PaymentStatus | None = None,
) -> Payment:
    if external_id is not None:
        payment.external_id = external_id
    if status_ is not None:
        payment.status = status_
    await session.commit()
    await session.refresh(payment)
    return payment


async def list_discounts(
    session: AsyncSession, user_id: int | None = None, limit: int = 50, offset: int = 0
) -> list[Discount]:
    stmt = select(Discount).order_by(Discount.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(Discount.user_id == user_id)
    result = await session.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all())


async def get_discount(session: AsyncSession, discount_id: int) -> Discount | None:
    return await session.get(Discount, discount_id)


async def create_discount(
    session: AsyncSession,
    user_id: int,
    title: str,
    code: str,
    percent_off: int,
    expires_at: datetime | None = None,
) -> Discount:
    discount = Discount(
        user_id=user_id, title=title, code=code, percent_off=percent_off, expires_at=expires_at
    )
    session.add(discount)
    await session.commit()
    await session.refresh(discount)
    return discount


async def update_discount(
    session: AsyncSession, discount: Discount, is_used: bool | None = None
) -> Discount:
    if is_used is not None:
        discount.is_used = is_used
    await session.commit()
    await session.refresh(discount)
    return discount


async def delete_discount(session: AsyncSession, discount: Discount) -> None:
    await session.delete(discount)
    await session.commit()


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


async def list_hospitals(
    session: AsyncSession,
    category_id: int | None = None,
    city: str | None = None,
    sort: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Hospital]:
    stmt = select(Hospital).where(Hospital.is_deleted.is_(False))
    if category_id is not None:
        stmt = (
            stmt.join(Doctor, Doctor.hospital_id == Hospital.id)
            .where(Doctor.medical_category_id == category_id)
            .distinct()
        )
    if city is not None:
        stmt = stmt.where(Hospital.city.ilike(city))

    if sort == "distance" and lat is not None and lng is not None:
        hospitals = list((await session.execute(stmt)).scalars().all())
        hospitals.sort(key=lambda h: _haversine_km(lat, lng, h.lat, h.lng))
        return hospitals[offset : offset + limit]

    stmt = stmt.order_by(Hospital.rating_avg.desc() if sort == "rating" else Hospital.id)
    stmt = stmt.limit(limit).offset(offset)
    return list((await session.execute(stmt)).scalars().all())


async def get_hospital(session: AsyncSession, hospital_id: int) -> Hospital | None:
    hospital = await session.get(Hospital, hospital_id)
    if hospital is None or hospital.is_deleted:
        return None
    return hospital


async def create_hospital(
    session: AsyncSession,
    name: str,
    address: str,
    city: str,
    lat: float,
    lng: float,
    phone_numbers: list[str] | None = None,
    working_hours: dict | None = None,
) -> Hospital:
    hospital = Hospital(
        name=name,
        address=address,
        city=city,
        lat=lat,
        lng=lng,
        phone_numbers=phone_numbers or [],
        working_hours=working_hours or {},
    )
    session.add(hospital)
    await session.commit()
    await session.refresh(hospital)
    return hospital


async def update_hospital(
    session: AsyncSession,
    hospital: Hospital,
    name: str | None = None,
    address: str | None = None,
    city: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    phone_numbers: list[str] | None = None,
    working_hours: dict | None = None,
) -> Hospital:
    if name is not None:
        hospital.name = name
    if address is not None:
        hospital.address = address
    if city is not None:
        hospital.city = city
    if lat is not None:
        hospital.lat = lat
    if lng is not None:
        hospital.lng = lng
    if phone_numbers is not None:
        hospital.phone_numbers = phone_numbers
    if working_hours is not None:
        hospital.working_hours = working_hours
    await session.commit()
    await session.refresh(hospital)
    return hospital


async def soft_delete_hospital(session: AsyncSession, hospital: Hospital) -> None:
    hospital.is_deleted = True
    await session.commit()


async def list_doctors_by_hospital(session: AsyncSession, hospital_id: int) -> list[Doctor]:
    result = await session.execute(select(Doctor).where(Doctor.hospital_id == hospital_id))
    return list(result.scalars().all())


async def list_hospital_leaderboard(
    session: AsyncSession, category_id: int | None = None
) -> list[tuple[Hospital, float]]:
    stmt = select(Hospital).where(Hospital.is_deleted.is_(False))
    if category_id is not None:
        stmt = (
            stmt.join(Doctor, Doctor.hospital_id == Hospital.id)
            .where(Doctor.medical_category_id == category_id)
            .distinct()
        )
    hospitals = list((await session.execute(stmt)).scalars().all())

    count_stmt = select(Appointment.hospital_id, func.count(Appointment.id)).group_by(
        Appointment.hospital_id
    )
    counts = dict((await session.execute(count_stmt)).all())

    ranked = []
    for hospital in hospitals:
        appointment_count = counts.get(hospital.id, 0)
        # blend quality (rating) with popularity (appointment volume, capped so no single hospital dominates)
        weighted_score = round(
            hospital.rating_avg * 0.7 + min(appointment_count, 100) / 100 * 5 * 0.3, 2
        )
        ranked.append((hospital, weighted_score))
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return ranked


async def list_doctors(
    session: AsyncSession,
    hospital_id: int | None = None,
    category_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Doctor]:
    stmt = select(Doctor).order_by(Doctor.id)
    if hospital_id is not None:
        stmt = stmt.where(Doctor.hospital_id == hospital_id)
    if category_id is not None:
        stmt = stmt.where(Doctor.medical_category_id == category_id)
    result = await session.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all())


async def get_doctor(session: AsyncSession, doctor_id: int) -> Doctor | None:
    return await session.get(Doctor, doctor_id)


async def create_doctor(
    session: AsyncSession,
    hospital_id: int,
    medical_category_id: int,
    full_name: str,
    experience_years: int = 0,
) -> Doctor:
    doctor = Doctor(
        hospital_id=hospital_id,
        medical_category_id=medical_category_id,
        full_name=full_name,
        experience_years=experience_years,
    )
    session.add(doctor)
    await session.commit()
    await session.refresh(doctor)
    return doctor


async def update_doctor(
    session: AsyncSession,
    doctor: Doctor,
    hospital_id: int | None = None,
    medical_category_id: int | None = None,
    full_name: str | None = None,
    experience_years: int | None = None,
) -> Doctor:
    if hospital_id is not None:
        doctor.hospital_id = hospital_id
    if medical_category_id is not None:
        doctor.medical_category_id = medical_category_id
    if full_name is not None:
        doctor.full_name = full_name
    if experience_years is not None:
        doctor.experience_years = experience_years
    await session.commit()
    await session.refresh(doctor)
    return doctor


async def delete_doctor(session: AsyncSession, doctor: Doctor) -> None:
    await session.delete(doctor)
    await session.commit()


async def list_medical_categories(
    session: AsyncSession, limit: int = 50, offset: int = 0
) -> list[MedicalCategory]:
    result = await session.execute(
        select(MedicalCategory).order_by(MedicalCategory.id).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def get_medical_category(session: AsyncSession, category_id: int) -> MedicalCategory | None:
    return await session.get(MedicalCategory, category_id)


async def create_medical_category(session: AsyncSession, name: str) -> MedicalCategory:
    category = MedicalCategory(name=name)
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


async def update_medical_category(
    session: AsyncSession, category: MedicalCategory, name: str | None = None
) -> MedicalCategory:
    if name is not None:
        category.name = name
    await session.commit()
    await session.refresh(category)
    return category


async def delete_medical_category(session: AsyncSession, category: MedicalCategory) -> None:
    await session.delete(category)
    await session.commit()


async def list_feedback(
    session: AsyncSession,
    user_id: int | None = None,
    hospital_id: int | None = None,
    category_id: int | None = None,
    sentiment: FeedbackSentiment | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Feedback]:
    stmt = select(Feedback).order_by(Feedback.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(Feedback.user_id == user_id)
    if hospital_id is not None:
        stmt = stmt.where(Feedback.hospital_id == hospital_id)
    if category_id is not None:
        stmt = stmt.where(Feedback.category_id == category_id)
    if sentiment is not None:
        stmt = stmt.where(Feedback.sentiment == sentiment)
    if date_from is not None:
        stmt = stmt.where(Feedback.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Feedback.created_at <= date_to)
    result = await session.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all())


async def get_feedback(session: AsyncSession, feedback_id: int) -> Feedback | None:
    return await session.get(Feedback, feedback_id)


async def create_feedback(
    session: AsyncSession,
    user_id: int,
    appointment_id: int,
    hospital_id: int | None = None,
    doctor_id: int | None = None,
    category_id: int | None = None,
    answers: list[dict] | None = None,
    audio_file: str | None = None,
) -> Feedback:
    feedback = Feedback(
        user_id=user_id,
        appointment_id=appointment_id,
        hospital_id=hospital_id,
        doctor_id=doctor_id,
        category_id=category_id,
        answers=answers or [],
        audio_file=audio_file,
        processing_status=FeedbackProcessingStatus.pending,
    )
    session.add(feedback)
    await session.commit()
    await session.refresh(feedback)
    return feedback


async def update_feedback_processing(
    session: AsyncSession,
    feedback: Feedback,
    transcript: str | None = None,
    sentiment: FeedbackSentiment | None = None,
    keywords: list[str] | None = None,
    processing_status: FeedbackProcessingStatus | None = None,
) -> Feedback:
    if transcript is not None:
        feedback.transcript = transcript
    if sentiment is not None:
        feedback.sentiment = sentiment
    if keywords is not None:
        feedback.keywords = keywords
    if processing_status is not None:
        feedback.processing_status = processing_status
    await session.commit()
    await session.refresh(feedback)
    return feedback


async def list_audit_log(session: AsyncSession, limit: int = 50, offset: int = 0) -> list[AuditLog]:
    result = await session.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def create_audit_log(
    session: AsyncSession, actor_id: int, action: str, entity: str, entity_id: int | None = None
) -> AuditLog:
    entry = AuditLog(actor_id=actor_id, action=action, entity=entity, entity_id=entity_id)
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def get_stats_overview(session: AsyncSession) -> dict:
    users_count = (await session.execute(select(func.count(User.id)))).scalar_one()
    appointments_count = (await session.execute(select(func.count(Appointment.id)))).scalar_one()
    feedback_count = (await session.execute(select(func.count(Feedback.id)))).scalar_one()
    # TODO: no payment/billing table exists yet — revenue is a placeholder derived from
    # redeemed discounts (count of used discounts) until real transaction data lands.
    revenue = (
        await session.execute(select(func.count(Discount.id)).where(Discount.is_used.is_(True)))
    ).scalar_one()
    return {
        "users_count": users_count,
        "appointments_count": appointments_count,
        "feedback_count": feedback_count,
        "revenue": float(revenue),
    }


async def get_visits_by_category(
    session: AsyncSession, date_from: datetime | None = None, date_to: datetime | None = None
) -> list[tuple[int, str, int]]:
    stmt = (
        select(MedicalCategory.id, MedicalCategory.name, func.count(Appointment.id))
        .join(Doctor, Doctor.medical_category_id == MedicalCategory.id)
        .join(Appointment, Appointment.doctor_id == Doctor.id)
        .group_by(MedicalCategory.id, MedicalCategory.name)
        .order_by(MedicalCategory.id)
    )
    if date_from is not None:
        stmt = stmt.where(Appointment.scheduled_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Appointment.scheduled_at <= date_to)
    result = await session.execute(stmt)
    return [(row[0], row[1], row[2]) for row in result.all()]
