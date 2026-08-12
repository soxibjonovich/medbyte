import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Query, UploadFile, status

from . import database_client, rabbitmq_client, rate_limit
from .deps import get_current_user, require_admin
from .schemas import ClaimFeedbackResponse, Feedback, FeedbackTranscript, Question, Sentiment


class HealthLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(HealthLogFilter())

AUDIO_STORAGE_DIR = Path(os.environ.get("AUDIO_STORAGE_DIR", "audio_uploads"))

# The five doctor characteristics patients rate. Each is scored 1-5; the
# overall rating is their average (sum / 5).
CHARACTERISTICS = [
    ("professionalism", "Professionalism"),
    ("communication", "Communication"),
    ("punctuality", "Punctuality"),
    ("attentiveness", "Attentiveness"),
    ("effectiveness", "Effectiveness"),
]
MAX_RATING = len(CHARACTERISTICS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    AUDIO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    database_client.init_client()
    rate_limit.init_client()
    await rabbitmq_client.init_client()
    yield
    await rabbitmq_client.close_client()
    await rate_limit.close_client()
    await database_client.close_client()


app = FastAPI(lifespan=lifespan)
router = APIRouter(prefix="/api/feedback")


@app.get("/health")
async def health():
    return {"status": "ok"}


async def _store_audio(audio_file: UploadFile) -> str:
    suffix = Path(audio_file.filename or "").suffix
    stored_name = f"{uuid.uuid4()}{suffix}"
    destination = AUDIO_STORAGE_DIR / stored_name
    with destination.open("wb") as out:
        while chunk := await audio_file.read(1024 * 1024):
            out.write(chunk)
    return str(destination)


async def _build_and_create_feedback(
    user_id: int,
    appointment: dict,
    professionalism: int,
    communication: int,
    punctuality: int,
    attentiveness: int,
    effectiveness: int,
    tags: list[str],
    text_comment: str | None,
    audio_file: UploadFile | None,
) -> dict:
    """Shared by the logged-in create_feedback endpoint and the unauthenticated
    claim-by-token endpoint: validates ratings, builds the answers payload,
    derives category_id, stores audio, creates the feedback row, and — if
    audio was submitted — publishes the STT job."""
    submitted = (
        professionalism,
        communication,
        punctuality,
        attentiveness,
        effectiveness,
    )
    rating_values = {
        key: value for (key, _), value in zip(CHARACTERISTICS, submitted)
    }
    for key, value in rating_values.items():
        if not isinstance(value, int) or not 1 <= value <= 5:
            raise HTTPException(
                status_code=422, detail=f"{key} must be an integer between 1 and 5"
            )

    # Average of the five characteristic ratings — the overall score (sum / 5).
    rating_avg = sum(rating_values.values()) / MAX_RATING

    answers = [
        {"question_id": index + 1, "question": label, "rating": rating_values[key], "comment": None}
        for index, (key, label) in enumerate(CHARACTERISTICS)
    ]
    if text_comment:
        answers.append(
            {
                "question_id": 0,
                "question": "Additional comments",
                "rating": None,
                "comment": text_comment,
            }
        )
    if tags:
        answers.append(
            {
                "question_id": -1,
                "question": "What they liked",
                "rating": None,
                "comment": ", ".join(tags),
            }
        )

    category_id = None
    if appointment.get("doctor_id") is not None:
        doctor = await database_client.get_or_none(f"/doctors/{appointment['doctor_id']}")
        if doctor is not None:
            category_id = doctor["medical_category_id"]

    stored_audio_path = await _store_audio(audio_file) if audio_file is not None else None

    created = await database_client.post(
        "/feedback",
        json={
            "user_id": user_id,
            "appointment_id": appointment["id"],
            "hospital_id": appointment.get("hospital_id"),
            "doctor_id": appointment.get("doctor_id"),
            "category_id": category_id,
            "rating": rating_avg,
            "tags": tags,
            "text_comment": text_comment,
            "answers": answers,
            "audio_file": stored_audio_path,
        },
    )

    if stored_audio_path is not None:
        await rabbitmq_client.publish_stt_job(created["id"], stored_audio_path)

    return created


@router.post(
    "",
    response_model=Feedback,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(rate_limit.rate_limit_dependency("create_feedback", limit=20, window_seconds=60))
    ],
)
async def create_feedback(
    appointment_id: int = Form(...),
    professionalism: int = Form(...),
    communication: int = Form(...),
    punctuality: int = Form(...),
    attentiveness: int = Form(...),
    effectiveness: int = Form(...),
    tags: list[str] = Form(default=[]),
    text_comment: str | None = Form(default=None),
    audio_file: UploadFile | None = None,
    current_user: dict = Depends(get_current_user),
):
    appointment = await database_client.get_or_none(f"/appointments/{appointment_id}")
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="appointment not found")
    if appointment["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not your appointment"
        )

    return await _build_and_create_feedback(
        current_user["id"],
        appointment,
        professionalism,
        communication,
        punctuality,
        attentiveness,
        effectiveness,
        tags,
        text_comment,
        audio_file,
    )


@router.post(
    "/claim/{token}",
    response_model=ClaimFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(rate_limit.rate_limit_dependency("claim_feedback", limit=10, window_seconds=60))
    ],
)
async def claim_feedback(
    token: str,
    professionalism: int = Form(...),
    communication: int = Form(...),
    punctuality: int = Form(...),
    attentiveness: int = Form(...),
    effectiveness: int = Form(...),
    tags: list[str] = Form(default=[]),
    text_comment: str | None = Form(default=None),
    audio_file: UploadFile | None = None,
):
    """Unauthenticated: submit feedback via a one-time link (minted when a payment
    succeeds) instead of being logged in. Redeems the token and, if the token was
    still unused, tries to award a random pool discount to the token's owner."""
    token_record = await database_client.get_or_none(f"/feedback-tokens/by-token/{token}")
    if token_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invalid link")
    if token_record["used"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="link already used")

    appointment = await database_client.get_or_none(
        f"/appointments/{token_record['appointment_id']}"
    )
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="appointment not found")

    created = await _build_and_create_feedback(
        token_record["user_id"],
        appointment,
        professionalism,
        communication,
        punctuality,
        attentiveness,
        effectiveness,
        tags,
        text_comment,
        audio_file,
    )

    await database_client.post(f"/feedback-tokens/{token}/redeem", json={})

    discount = None
    try:
        discount = await database_client.post(
            "/discounts/award-random", json={"user_id": token_record["user_id"]}
        )
    except HTTPException:
        # 404 "no discounts available" is an expected, non-fatal outcome — the
        # feedback must still be saved and returned even with no discount.
        pass

    return ClaimFeedbackResponse(feedback=created, discount=discount)


@router.get("/questions/{appointment_id}", response_model=list[Question])
async def get_appointment_questions(
    appointment_id: int, current_user: dict = Depends(get_current_user)
):
    appointment = await database_client.get_or_none(f"/appointments/{appointment_id}")
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="appointment not found")
    if appointment["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not your appointment"
        )
    if appointment.get("hospital_id") is None:
        return []
    questions = await database_client.get_or_none(
        f"/questions?hospital_id={appointment['hospital_id']}"
    )
    return questions or []


@router.get("/{feedback_id}", response_model=Feedback)
async def get_feedback(feedback_id: int, current_user: dict = Depends(get_current_user)):
    feedback = await database_client.get_or_none(f"/feedback/{feedback_id}")
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="feedback not found")
    if feedback["user_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not your feedback")
    return feedback


@router.get("", response_model=list[Feedback])
async def list_feedback(
    hospital_id: int | None = Query(default=None),
    category_id: int | None = Query(default=None),
    sentiment: Sentiment | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: dict = Depends(require_admin),
):
    params = {
        k: v
        for k, v in {
            "hospital_id": hospital_id,
            "category_id": category_id,
            "sentiment": sentiment,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return await database_client.get(f"/feedback?{urlencode(params)}")


@router.get("/{feedback_id}/transcript", response_model=FeedbackTranscript)
async def get_feedback_transcript(feedback_id: int, _: dict = Depends(require_admin)):
    transcript = await database_client.get_or_none(f"/feedback/{feedback_id}/transcript")
    if transcript is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="feedback not found")
    return transcript


app.include_router(router)
