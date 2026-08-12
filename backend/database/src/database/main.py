from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud
from .models import FeedbackSentiment
from .schemas import (
    AppointmentResponse,
    AuditLogResponse,
    CategoryVisitStat,
    CreateAppointmentRequest,
    CreateAuditLogRequest,
    CreateDiscountRequest,
    CreateDoctorRequest,
    CreateFeedbackRequest,
    CreateHospitalRequest,
    CreateMedicalCategoryRequest,
    CreateNotificationRequest,
    CreateQuestionRequest,
    CreateUserRequest,
    DiscountResponse,
    DoctorResponse,
    FeedbackResponse,
    FeedbackTranscriptResponse,
    HospitalDetailResponse,
    HospitalLeaderboardEntry,
    HospitalResponse,
    MedicalCategoryResponse,
    CreatePaymentRequest,
    NotificationResponse,
    PaymentResponse,
    QuestionResponse,
    StatsOverview,
    UpdateAppointmentRequest,
    UpdateDiscountRequest,
    UpdateDoctorRequest,
    UpdateFeedbackProcessingRequest,
    UpdateHospitalRequest,
    UpdateMedicalCategoryRequest,
    UpdateNotificationRequest,
    UpdatePaymentRequest,
    UpdateQuestionRequest,
    UpdateUserRequest,
    UserResponse,
    UserWithSecret,
)
from .session import get_session, init_models


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_models()
    yield


app = FastAPI(root_path="/api/v1/database", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/users", response_model=list[UserResponse])
async def list_users_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await crud.list_users(session, limit=limit, offset=offset)


@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    payload: CreateUserRequest, session: AsyncSession = Depends(get_session)
):
    if (
        payload.username
        and await crud.get_user_by_username(session, payload.username) is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="username already registered"
        )
    if payload.phone and await crud.get_user_by_phone(session, payload.phone) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="phone already registered"
        )
    if payload.email and await crud.get_user_by_email(session, payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="email already registered"
        )

    return await crud.create_user(
        session,
        full_name=payload.full_name,
        username=payload.username,
        phone=payload.phone,
        email=payload.email,
        password_hash=payload.password_hash,
        role=payload.role,
    )


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user_endpoint(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await crud.get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user


@app.get(
    "/users/by-username/{username}", response_model=UserWithSecret, include_in_schema=False
)
async def get_user_by_username_endpoint(
    username: str, session: AsyncSession = Depends(get_session)
):
    """Internal lookup for other services (e.g. auth) — includes password_hash."""
    user = await crud.get_user_by_username(session, username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user


@app.get("/users/by-phone/{phone}", response_model=UserWithSecret, include_in_schema=False)
async def get_user_by_phone_endpoint(phone: str, session: AsyncSession = Depends(get_session)):
    """Internal lookup for other services (e.g. auth) — includes password_hash."""
    user = await crud.get_user_by_phone(session, phone)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user


@app.get("/users/by-email/{email}", response_model=UserWithSecret, include_in_schema=False)
async def get_user_by_email_endpoint(email: str, session: AsyncSession = Depends(get_session)):
    """Internal lookup for other services (e.g. auth) — includes password_hash."""
    user = await crud.get_user_by_email(session, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user


@app.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_endpoint(
    user_id: int, payload: UpdateUserRequest, session: AsyncSession = Depends(get_session)
):
    user = await crud.get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    if payload.username and payload.username != user.username:
        if await crud.get_user_by_username(session, payload.username) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="username already registered"
            )
    if payload.phone and payload.phone != user.phone:
        if await crud.get_user_by_phone(session, payload.phone) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="phone already registered"
            )
    if payload.email and payload.email != user.email:
        if await crud.get_user_by_email(session, payload.email) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="email already registered"
            )

    return await crud.update_user(
        session,
        user,
        full_name=payload.full_name,
        username=payload.username,
        phone=payload.phone,
        email=payload.email,
        role=payload.role,
    )


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await crud.get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    await crud.delete_user(session, user)


@app.get("/appointments", response_model=list[AppointmentResponse])
async def list_appointments_endpoint(
    user_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await crud.list_appointments(session, user_id=user_id, limit=limit, offset=offset)


@app.post("/appointments", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment_endpoint(
    payload: CreateAppointmentRequest, session: AsyncSession = Depends(get_session)
):
    if await crud.get_user(session, payload.user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return await crud.create_appointment(
        session,
        user_id=payload.user_id,
        scheduled_at=payload.scheduled_at,
        hospital_id=payload.hospital_id,
        doctor_id=payload.doctor_id,
        queue_number=payload.queue_number,
        status_=payload.status,
    )


@app.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment_endpoint(appointment_id: int, session: AsyncSession = Depends(get_session)):
    appointment = await crud.get_appointment(session, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="appointment not found")
    return appointment


@app.patch("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment_endpoint(
    appointment_id: int,
    payload: UpdateAppointmentRequest,
    session: AsyncSession = Depends(get_session),
):
    appointment = await crud.get_appointment(session, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="appointment not found")
    return await crud.update_appointment(
        session,
        appointment,
        hospital_id=payload.hospital_id,
        doctor_id=payload.doctor_id,
        queue_number=payload.queue_number,
        status_=payload.status,
        scheduled_at=payload.scheduled_at,
    )


@app.post(
    "/appointments/{appointment_id}/assign-queue", response_model=AppointmentResponse
)
async def assign_queue_number_endpoint(
    appointment_id: int, session: AsyncSession = Depends(get_session)
):
    appointment = await crud.get_appointment(session, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="appointment not found")
    return await crud.assign_queue_number(session, appointment)


@app.delete("/appointments/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment_endpoint(appointment_id: int, session: AsyncSession = Depends(get_session)):
    appointment = await crud.get_appointment(session, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="appointment not found")
    await crud.delete_appointment(session, appointment)


@app.get("/notifications", response_model=list[NotificationResponse])
async def list_notifications_endpoint(
    user_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await crud.list_notifications(session, user_id=user_id, limit=limit, offset=offset)


@app.post("/notifications", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification_endpoint(
    payload: CreateNotificationRequest, session: AsyncSession = Depends(get_session)
):
    if await crud.get_user(session, payload.user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return await crud.create_notification(
        session, user_id=payload.user_id, title=payload.title, message=payload.message
    )


@app.get("/notifications/{notification_id}", response_model=NotificationResponse)
async def get_notification_endpoint(
    notification_id: int, session: AsyncSession = Depends(get_session)
):
    notification = await crud.get_notification(session, notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")
    return notification


@app.patch("/notifications/{notification_id}", response_model=NotificationResponse)
async def update_notification_endpoint(
    notification_id: int,
    payload: UpdateNotificationRequest,
    session: AsyncSession = Depends(get_session),
):
    notification = await crud.get_notification(session, notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")
    return await crud.update_notification(session, notification, is_read=payload.is_read)


@app.delete("/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_endpoint(
    notification_id: int, session: AsyncSession = Depends(get_session)
):
    notification = await crud.get_notification(session, notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")
    await crud.delete_notification(session, notification)


@app.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_endpoint(
    payload: CreatePaymentRequest, session: AsyncSession = Depends(get_session)
):
    if await crud.get_user(session, payload.user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    if await crud.get_appointment(session, payload.appointment_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="appointment not found")
    return await crud.create_payment(
        session,
        user_id=payload.user_id,
        appointment_id=payload.appointment_id,
        provider=payload.provider,
        amount=payload.amount,
        currency=payload.currency,
    )


@app.get("/payments/by-external/{external_id}", response_model=PaymentResponse, include_in_schema=False)
async def get_payment_by_external_endpoint(
    external_id: str, session: AsyncSession = Depends(get_session)
):
    """Internal lookup for the payment service's provider webhook handlers."""
    payment = await crud.get_payment_by_external_id(session, external_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment not found")
    return payment


@app.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment_endpoint(payment_id: int, session: AsyncSession = Depends(get_session)):
    payment = await crud.get_payment(session, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment not found")
    return payment


@app.patch("/payments/{payment_id}", response_model=PaymentResponse)
async def update_payment_endpoint(
    payment_id: int, payload: UpdatePaymentRequest, session: AsyncSession = Depends(get_session)
):
    payment = await crud.get_payment(session, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment not found")
    return await crud.update_payment(
        session, payment, external_id=payload.external_id, status_=payload.status
    )


@app.get("/discounts", response_model=list[DiscountResponse])
async def list_discounts_endpoint(
    user_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await crud.list_discounts(session, user_id=user_id, limit=limit, offset=offset)


@app.post("/discounts", response_model=DiscountResponse, status_code=status.HTTP_201_CREATED)
async def create_discount_endpoint(
    payload: CreateDiscountRequest, session: AsyncSession = Depends(get_session)
):
    if await crud.get_user(session, payload.user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return await crud.create_discount(
        session,
        user_id=payload.user_id,
        title=payload.title,
        code=payload.code,
        percent_off=payload.percent_off,
        expires_at=payload.expires_at,
    )


@app.get("/discounts/{discount_id}", response_model=DiscountResponse)
async def get_discount_endpoint(discount_id: int, session: AsyncSession = Depends(get_session)):
    discount = await crud.get_discount(session, discount_id)
    if discount is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="discount not found")
    return discount


@app.patch("/discounts/{discount_id}", response_model=DiscountResponse)
async def update_discount_endpoint(
    discount_id: int, payload: UpdateDiscountRequest, session: AsyncSession = Depends(get_session)
):
    discount = await crud.get_discount(session, discount_id)
    if discount is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="discount not found")
    return await crud.update_discount(session, discount, is_used=payload.is_used)


@app.delete("/discounts/{discount_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_discount_endpoint(discount_id: int, session: AsyncSession = Depends(get_session)):
    discount = await crud.get_discount(session, discount_id)
    if discount is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="discount not found")
    await crud.delete_discount(session, discount)


@app.get("/hospitals", response_model=list[HospitalResponse])
async def list_hospitals_endpoint(
    category: int | None = Query(default=None),
    city: str | None = Query(default=None),
    sort: str | None = Query(default=None, pattern="^(rating|distance)$"),
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await crud.list_hospitals(
        session,
        category_id=category,
        city=city,
        sort=sort,
        lat=lat,
        lng=lng,
        limit=limit,
        offset=offset,
    )


@app.get("/hospitals/leaderboard", response_model=list[HospitalLeaderboardEntry])
async def hospital_leaderboard_endpoint(
    category: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    ranked = await crud.list_hospital_leaderboard(session, category_id=category)
    return [
        HospitalLeaderboardEntry(
            rank=i + 1,
            id=hospital.id,
            name=hospital.name,
            city=hospital.city,
            rating_avg=hospital.rating_avg,
            weighted_score=weighted_score,
        )
        for i, (hospital, weighted_score) in enumerate(ranked)
    ]


@app.post("/hospitals", response_model=HospitalResponse, status_code=status.HTTP_201_CREATED)
async def create_hospital_endpoint(
    payload: CreateHospitalRequest, session: AsyncSession = Depends(get_session)
):
    return await crud.create_hospital(
        session,
        name=payload.name,
        address=payload.address,
        city=payload.city,
        lat=payload.lat,
        lng=payload.lng,
        phone_numbers=payload.phone_numbers,
        working_hours=payload.working_hours,
    )


@app.get("/hospitals/{hospital_id}", response_model=HospitalDetailResponse)
async def get_hospital_endpoint(hospital_id: int, session: AsyncSession = Depends(get_session)):
    hospital = await crud.get_hospital(session, hospital_id)
    if hospital is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hospital not found")
    doctors = await crud.list_doctors_by_hospital(session, hospital_id)
    return HospitalDetailResponse(
        **HospitalResponse.model_validate(hospital).model_dump(),
        phone_numbers=hospital.phone_numbers,
        working_hours=hospital.working_hours,
        doctors=doctors,
    )


@app.patch("/hospitals/{hospital_id}", response_model=HospitalResponse)
async def update_hospital_endpoint(
    hospital_id: int, payload: UpdateHospitalRequest, session: AsyncSession = Depends(get_session)
):
    hospital = await crud.get_hospital(session, hospital_id)
    if hospital is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hospital not found")
    return await crud.update_hospital(
        session,
        hospital,
        name=payload.name,
        address=payload.address,
        city=payload.city,
        lat=payload.lat,
        lng=payload.lng,
        phone_numbers=payload.phone_numbers,
        working_hours=payload.working_hours,
    )


@app.delete("/hospitals/{hospital_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hospital_endpoint(hospital_id: int, session: AsyncSession = Depends(get_session)):
    hospital = await crud.get_hospital(session, hospital_id)
    if hospital is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hospital not found")
    await crud.soft_delete_hospital(session, hospital)


@app.get("/doctors", response_model=list[DoctorResponse])
async def list_doctors_endpoint(
    hospital_id: int | None = Query(default=None),
    category: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await crud.list_doctors(
        session, hospital_id=hospital_id, category_id=category, limit=limit, offset=offset
    )


@app.post("/doctors", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor_endpoint(
    payload: CreateDoctorRequest, session: AsyncSession = Depends(get_session)
):
    if await crud.get_hospital(session, payload.hospital_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hospital not found")
    if await crud.get_medical_category(session, payload.medical_category_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="medical category not found")
    return await crud.create_doctor(
        session,
        hospital_id=payload.hospital_id,
        medical_category_id=payload.medical_category_id,
        full_name=payload.full_name,
        experience_years=payload.experience_years,
    )


@app.get("/doctors/{doctor_id}", response_model=DoctorResponse)
async def get_doctor_endpoint(doctor_id: int, session: AsyncSession = Depends(get_session)):
    doctor = await crud.get_doctor(session, doctor_id)
    if doctor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="doctor not found")
    return doctor


@app.patch("/doctors/{doctor_id}", response_model=DoctorResponse)
async def update_doctor_endpoint(
    doctor_id: int, payload: UpdateDoctorRequest, session: AsyncSession = Depends(get_session)
):
    doctor = await crud.get_doctor(session, doctor_id)
    if doctor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="doctor not found")
    return await crud.update_doctor(
        session,
        doctor,
        hospital_id=payload.hospital_id,
        medical_category_id=payload.medical_category_id,
        full_name=payload.full_name,
        experience_years=payload.experience_years,
    )


@app.delete("/doctors/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doctor_endpoint(doctor_id: int, session: AsyncSession = Depends(get_session)):
    doctor = await crud.get_doctor(session, doctor_id)
    if doctor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="doctor not found")
    await crud.delete_doctor(session, doctor)


@app.get("/medical-categories", response_model=list[MedicalCategoryResponse])
async def list_medical_categories_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await crud.list_medical_categories(session, limit=limit, offset=offset)


@app.post(
    "/medical-categories", response_model=MedicalCategoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_medical_category_endpoint(
    payload: CreateMedicalCategoryRequest, session: AsyncSession = Depends(get_session)
):
    return await crud.create_medical_category(session, name=payload.name)


@app.get("/medical-categories/{category_id}", response_model=MedicalCategoryResponse)
async def get_medical_category_endpoint(
    category_id: int, session: AsyncSession = Depends(get_session)
):
    category = await crud.get_medical_category(session, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="medical category not found")
    return category


@app.patch("/medical-categories/{category_id}", response_model=MedicalCategoryResponse)
async def update_medical_category_endpoint(
    category_id: int,
    payload: UpdateMedicalCategoryRequest,
    session: AsyncSession = Depends(get_session),
):
    category = await crud.get_medical_category(session, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="medical category not found")
    return await crud.update_medical_category(session, category, name=payload.name)


@app.delete("/medical-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medical_category_endpoint(
    category_id: int, session: AsyncSession = Depends(get_session)
):
    category = await crud.get_medical_category(session, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="medical category not found")
    await crud.delete_medical_category(session, category)


@app.get("/questions", response_model=list[QuestionResponse])
async def list_questions_endpoint(
    hospital_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await crud.list_questions(
        session, hospital_id=hospital_id, limit=limit, offset=offset
    )


@app.post("/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question_endpoint(
    payload: CreateQuestionRequest, session: AsyncSession = Depends(get_session)
):
    if await crud.get_hospital(session, payload.hospital_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hospital not found")
    return await crud.create_question(
        session, hospital_id=payload.hospital_id, text=payload.text, position=payload.position
    )


@app.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question_endpoint(question_id: int, session: AsyncSession = Depends(get_session)):
    question = await crud.get_question(session, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="question not found")
    return question


@app.patch("/questions/{question_id}", response_model=QuestionResponse)
async def update_question_endpoint(
    question_id: int,
    payload: UpdateQuestionRequest,
    session: AsyncSession = Depends(get_session),
):
    question = await crud.get_question(session, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="question not found")
    return await crud.update_question(
        session,
        question,
        text=payload.text,
        position=payload.position,
        is_active=payload.is_active,
    )


@app.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question_endpoint(question_id: int, session: AsyncSession = Depends(get_session)):
    question = await crud.get_question(session, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="question not found")
    await crud.delete_question(session, question)


@app.get("/feedback", response_model=list[FeedbackResponse])
async def list_feedback_endpoint(
    user_id: int | None = Query(default=None),
    hospital_id: int | None = Query(default=None),
    category_id: int | None = Query(default=None),
    sentiment: FeedbackSentiment | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await crud.list_feedback(
        session,
        user_id=user_id,
        hospital_id=hospital_id,
        category_id=category_id,
        sentiment=sentiment,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@app.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback_endpoint(
    payload: CreateFeedbackRequest, session: AsyncSession = Depends(get_session)
):
    if await crud.get_user(session, payload.user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    if await crud.get_appointment(session, payload.appointment_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="appointment not found")
    return await crud.create_feedback(
        session,
        user_id=payload.user_id,
        appointment_id=payload.appointment_id,
        hospital_id=payload.hospital_id,
        doctor_id=payload.doctor_id,
        category_id=payload.category_id,
        rating=payload.rating,
        tags=payload.tags,
        text_comment=payload.text_comment,
        answers=[answer.model_dump() for answer in payload.answers],
        audio_file=payload.audio_file,
    )


@app.get("/feedback/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_endpoint(feedback_id: int, session: AsyncSession = Depends(get_session)):
    feedback = await crud.get_feedback(session, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="feedback not found")
    return feedback


@app.get("/feedback/{feedback_id}/transcript", response_model=FeedbackTranscriptResponse)
async def get_feedback_transcript_endpoint(
    feedback_id: int, session: AsyncSession = Depends(get_session)
):
    feedback = await crud.get_feedback(session, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="feedback not found")
    return feedback


@app.patch(
    "/feedback/{feedback_id}/processing",
    response_model=FeedbackResponse,
    include_in_schema=False,
)
async def update_feedback_processing_endpoint(
    feedback_id: int,
    payload: UpdateFeedbackProcessingRequest,
    session: AsyncSession = Depends(get_session),
):
    """Internal: called by the STT/sentiment worker once a submission finishes processing."""
    feedback = await crud.get_feedback(session, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="feedback not found")
    return await crud.update_feedback_processing(
        session,
        feedback,
        transcript=payload.transcript,
        sentiment=payload.sentiment,
        keywords=payload.keywords,
        processing_status=payload.processing_status,
    )


@app.get("/audit-log", response_model=list[AuditLogResponse])
async def list_audit_log_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await crud.list_audit_log(session, limit=limit, offset=offset)


@app.post("/audit-log", response_model=AuditLogResponse, status_code=status.HTTP_201_CREATED)
async def create_audit_log_endpoint(
    payload: CreateAuditLogRequest, session: AsyncSession = Depends(get_session)
):
    """Internal: admin service logs its own mutating actions here."""
    return await crud.create_audit_log(
        session,
        actor_id=payload.actor_id,
        action=payload.action,
        entity=payload.entity,
        entity_id=payload.entity_id,
    )


@app.get("/stats/overview", response_model=StatsOverview)
async def stats_overview_endpoint(session: AsyncSession = Depends(get_session)):
    return await crud.get_stats_overview(session)


@app.get("/stats/by-category", response_model=list[CategoryVisitStat])
async def stats_by_category_endpoint(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    rows = await crud.get_visits_by_category(session, date_from=date_from, date_to=date_to)
    return [
        CategoryVisitStat(category_id=cid, category_name=name, visit_count=count)
        for cid, name, count in rows
    ]
