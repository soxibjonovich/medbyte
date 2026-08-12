from typing import Literal
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    id: int
    full_name: str
    username: str | None
    phone: str | None
    email: EmailStr | None
    role: Literal["patient", "staff", "admin"]
    created_at: datetime


class UpdateUser(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=9, max_length=20)
    email: EmailStr | None = None


class Appointment(BaseModel):
    id: int
    user_id: int
    hospital_id: int | None
    doctor_id: int | None
    queue_number: int | None
    status: Literal["scheduled", "completed", "cancelled"]
    scheduled_at: datetime
    created_at: datetime


class Notification(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime


class Discount(BaseModel):
    id: int
    user_id: int
    title: str
    code: str
    percent_off: int
    expires_at: datetime | None
    is_used: bool
    created_at: datetime