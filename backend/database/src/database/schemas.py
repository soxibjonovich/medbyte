from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import UserRole


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
    role: UserRole = UserRole.patient


class UpdateUserRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=9, max_length=20)
    email: EmailStr | None = None
    role: UserRole | None = None
