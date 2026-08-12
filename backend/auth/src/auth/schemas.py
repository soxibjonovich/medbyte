from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CreateUser(BaseModel):
    full_name: str = Field(
        min_length=2, max_length=255, title="Full name", description="User's display name", examples=["Aziz Karimov"]
    )
    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        title="Username",
        description="Unique login handle, letters/digits/underscore only",
        examples=["aziz_k"],
    )
    phone: str | None = Field(
        default=None, min_length=9, max_length=20, title="Phone", description="Contact phone number", examples=["+998901234567"]
    )
    email: EmailStr | None = Field(
        default=None, title="Email", description="Contact email address", examples=["aziz@example.com"]
    )
    password: str = Field(
        min_length=8, title="Password", description="Plaintext password, hashed on the server before storage"
    )


class LoginUser(BaseModel):
    username: str = Field(title="Username", description="Login handle", examples=["aziz_k"])
    password: str = Field(title="Password", description="Account password")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique user id", examples=[1])
    full_name: str = Field(description="User's display name", examples=["Aziz Karimov"])
    username: str | None = Field(default=None, description="Unique login handle", examples=["aziz_k"])
    phone: str | None = Field(default=None, description="Contact phone number", examples=["+998901234567"])
    email: str | None = Field(default=None, description="Contact email", examples=["aziz@example.com"])
    role: str = Field(description="Access role: patient, staff, or admin", examples=["patient"])
    created_at: datetime = Field(description="Account creation timestamp (UTC)")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
