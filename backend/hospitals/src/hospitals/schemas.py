from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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


class HospitalLeaderboardEntry(BaseModel):
    rank: int
    id: int
    name: str
    city: str
    rating_avg: float
    weighted_score: float


SortOption = Literal["rating", "distance"]
