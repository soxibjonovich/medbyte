from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SortOption = Literal["rating", "distance"]


class DoctorSummary(BaseModel):
    id: int
    hospital_id: int
    medical_category_id: int
    full_name: str
    experience_years: int
    rating_avg: float


class Hospital(BaseModel):
    id: int
    name: str
    address: str
    city: str
    lat: float
    lng: float
    rating_avg: float
    created_at: datetime


class HospitalDetail(Hospital):
    phone_numbers: list[str]
    working_hours: dict
    doctors: list[DoctorSummary]


class CreateHospital(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1, max_length=500)
    city: str = Field(min_length=1, max_length=100)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    phone_numbers: list[str] = Field(default_factory=list)
    working_hours: dict = Field(default_factory=dict)


class UpdateHospital(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    phone_numbers: list[str] | None = None
    working_hours: dict | None = None


class Doctor(BaseModel):
    id: int
    hospital_id: int
    medical_category_id: int
    full_name: str
    experience_years: int
    rating_avg: float


class CreateDoctor(BaseModel):
    hospital_id: int
    medical_category_id: int
    full_name: str = Field(min_length=1, max_length=255)
    experience_years: int = Field(default=0, ge=0)


class UpdateDoctor(BaseModel):
    hospital_id: int | None = None
    medical_category_id: int | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    experience_years: int | None = Field(default=None, ge=0)


class MedicalCategory(BaseModel):
    id: int
    name: str


class CreateMedicalCategory(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class UpdateMedicalCategory(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class Discount(BaseModel):
    id: int
    user_id: int
    title: str
    code: str
    percent_off: int
    expires_at: datetime | None
    is_used: bool
    created_at: datetime


class CreateDiscount(BaseModel):
    user_id: int
    title: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    percent_off: int = Field(ge=1, le=100)
    expires_at: datetime | None = None


class UpdateDiscount(BaseModel):
    is_used: bool | None = None


class StatsOverview(BaseModel):
    users_count: int
    appointments_count: int
    feedback_count: int
    revenue: float


class CategoryVisitStat(BaseModel):
    category_id: int
    category_name: str
    visit_count: int


class QueueEntry(BaseModel):
    id: int
    user_id: int
    hospital_id: int | None
    doctor_id: int | None
    queue_number: int | None
    status: Literal["scheduled", "completed", "cancelled"]
    scheduled_at: datetime
    created_at: datetime


class CreateQueueEntry(BaseModel):
    user_id: int = Field(title="Patient id", description="Id of patient added to queue", examples=[1])
    hospital_id: int | None = Field(
        default=None, title="Hospital id", description="Hospital where patient queued", examples=[1]
    )
    doctor_id: int | None = Field(
        default=None, title="Doctor id", description="Doctor patient queued for", examples=[1]
    )
    queue_number: int | None = Field(
        default=None, title="Queue number", description="Position in queue", examples=[1]
    )
    scheduled_at: datetime = Field(title="Scheduled at", description="Queue entry time")


class AuditLogEntry(BaseModel):
    id: int
    actor_id: int
    action: str
    entity: str
    entity_id: int | None
    created_at: datetime
