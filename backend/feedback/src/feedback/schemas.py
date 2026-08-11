from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ProcessingStatus = Literal["pending", "processing", "done", "failed"]
Sentiment = Literal["positive", "neutral", "negative"]


class Feedback(BaseModel):
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
    sentiment: Sentiment | None
    processing_status: ProcessingStatus
    created_at: datetime


class FeedbackTranscript(BaseModel):
    id: int
    transcript: str | None
    sentiment: Sentiment | None
    keywords: list[str] | None
    processing_status: ProcessingStatus
