from datetime import datetime

from pydantic import BaseModel, Field


class Notification(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime


class PushSubscriptionKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=255)


class PushSubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=1, max_length=1000)
    keys: PushSubscriptionKeys


class PushSubscription(BaseModel):
    id: int
    user_id: int
    endpoint: str
    created_at: datetime


class TestEmailRequest(BaseModel):
    to: str | None = Field(default=None, max_length=255)
    subject: str = Field(default="Test email", max_length=255)
    body: str = Field(
        default="This is a test email from MedByte notifications service.",
        max_length=5000,
    )
