from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import AppointmentStatus, FeedbackProcessingStatus, FeedbackSentiment, UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    phone: str | None
    email: str | None
    role: UserRole
    created_at: datetime


class CreateUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=9, max_length=20)
    email: EmailStr | None = None
    password_hash: str | None = None
    role: UserRole = UserRole.patient


class UserWithSecret(UserResponse):
    """Internal, service-to-service only: includes password_hash. Never expose publicly."""

    password_hash: str | None = None


class UpdateUserRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=9, max_length=20)
    email: EmailStr | None = None
    role: UserRole | None = None


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    hospital_id: int | None
    doctor_id: int | None
    queue_number: int | None
    status: AppointmentStatus
    scheduled_at: datetime
    created_at: datetime


class CreateAppointmentRequest(BaseModel):
    user_id: int
    hospital_id: int | None = None
    doctor_id: int | None = None
    queue_number: int | None = None
    status: AppointmentStatus = AppointmentStatus.scheduled
    scheduled_at: datetime


class UpdateAppointmentRequest(BaseModel):
    hospital_id: int | None = None
    doctor_id: int | None = None
    queue_number: int | None = None
    status: AppointmentStatus | None = None
    scheduled_at: datetime | None = None


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime


class CreateNotificationRequest(BaseModel):
    user_id: int
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=1000)


class UpdateNotificationRequest(BaseModel):
    is_read: bool | None = None


class DiscountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    code: str
    percent_off: int
    expires_at: datetime | None
    is_used: bool
    created_at: datetime


class CreateDiscountRequest(BaseModel):
    user_id: int
    title: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    percent_off: int = Field(ge=1, le=100)
    expires_at: datetime | None = None


class UpdateDiscountRequest(BaseModel):
    is_used: bool | None = None


class DoctorSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hospital_id: int
    medical_category_id: int
    full_name: str
    experience_years: int
    rating_avg: float


class HospitalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    city: str
    lat: float
    lng: float
    rating_avg: float
    created_at: datetime


class HospitalDetailResponse(HospitalResponse):
    phone_numbers: list[str]
    working_hours: dict
    doctors: list[DoctorSummary]


class CreateHospitalRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1, max_length=500)
    city: str = Field(min_length=1, max_length=100)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    phone_numbers: list[str] = Field(default_factory=list)
    working_hours: dict = Field(default_factory=dict)


class UpdateHospitalRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    phone_numbers: list[str] | None = None
    working_hours: dict | None = None


class HospitalLeaderboardEntry(BaseModel):
    rank: int
    id: int
    name: str
    city: str
    rating_avg: float
    weighted_score: float


class MedicalCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CreateMedicalCategoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class UpdateMedicalCategoryRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class DoctorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hospital_id: int
    medical_category_id: int
    full_name: str
    experience_years: int
    rating_avg: float


class CreateDoctorRequest(BaseModel):
    hospital_id: int
    medical_category_id: int
    full_name: str = Field(min_length=1, max_length=255)
    experience_years: int = Field(default=0, ge=0)


class UpdateDoctorRequest(BaseModel):
    hospital_id: int | None = None
    medical_category_id: int | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    experience_years: int | None = Field(default=None, ge=0)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    appointment_id: int
    hospital_id: int | None
    doctor_id: int | None
    category_id: int | None
    rating: int
    tags: list[str]
    text_comment: str | None
    audio_file: str | None
    transcript: str | None
    sentiment: FeedbackSentiment | None
    processing_status: FeedbackProcessingStatus
    created_at: datetime


class FeedbackTranscriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transcript: str | None
    sentiment: FeedbackSentiment | None
    keywords: list[str] | None
    processing_status: FeedbackProcessingStatus


class CreateFeedbackRequest(BaseModel):
    user_id: int
    appointment_id: int
    hospital_id: int | None = None
    doctor_id: int | None = None
    category_id: int | None = None
    rating: int = Field(ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    text_comment: str | None = Field(default=None, max_length=2000)
    audio_file: str | None = None


class UpdateFeedbackProcessingRequest(BaseModel):
    transcript: str | None = None
    sentiment: FeedbackSentiment | None = None
    keywords: list[str] | None = None
    processing_status: FeedbackProcessingStatus | None = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int
    action: str
    entity: str
    entity_id: int | None
    created_at: datetime


class CreateAuditLogRequest(BaseModel):
    actor_id: int
    action: str = Field(min_length=1, max_length=50)
    entity: str = Field(min_length=1, max_length=50)
    entity_id: int | None = None


class CategoryVisitStat(BaseModel):
    category_id: int
    category_name: str
    visit_count: int


class StatsOverview(BaseModel):
    users_count: int
    appointments_count: int
    feedback_count: int
    revenue: float
