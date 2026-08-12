from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ProcessingStatus = Literal["pending", "processing", "done", "failed"]
Sentiment = Literal["positive", "neutral", "negative"]


class FeedbackAnswer(BaseModel):
    question_id: int
    question: str
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class Question(BaseModel):
    id: int
    hospital_id: int
    text: str
    position: int
    is_active: bool


class Feedback(BaseModel):
    id: int
    user_id: int
    appointment_id: int
    hospital_id: int | None
    doctor_id: int | None
    category_id: int | None
    rating: float | None = Field(default=None, ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    text_comment: str | None = None
    answers: list[FeedbackAnswer]
    audio_file: str | None
    transcript: str | None
    sentiment: Sentiment | None
    processing_status: ProcessingStatus
    created_at: datetime


class FeedbackTranscript(BaseModel):
    id: int
    transcript: str | None
    sentiment: Sentiment | None
    keywords: list[str] | None
    processing_status: ProcessingStatus


class DiscountAward(BaseModel):
    """Local mirror of the database service's DiscountResponse — services don't
    share schema modules, so this is redefined here for the claim-link response."""

    id: int
    user_id: int | None
    title: str
    code: str
    percent_off: int
    expires_at: datetime | None
    is_used: bool
    created_at: datetime


class ClaimFeedbackResponse(BaseModel):
    feedback: Feedback
    discount: DiscountAward | None = None
