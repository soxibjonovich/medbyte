from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CreateUser(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=9, max_length=20)
    email: EmailStr | None = None
    password: str = Field(min_length=8)


class LoginUser(BaseModel):
    phone: str = Field()
    password: str = Field()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    phone: str | None
    email: str | None
    role: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
