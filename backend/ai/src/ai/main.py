from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Form, UploadFile

from . import database_client, llm_client, stt_client
from .deps import get_current_user
from .schemas import AudioTranscriptResponse, ChatRequest, ChatResponse


@asynccontextmanager
async def lifespan(_: FastAPI):
    database_client.init_client()
    yield
    await database_client.close_client()


app = FastAPI(lifespan=lifespan)
router = APIRouter(prefix="/api/ai")


@app.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, current_user: dict = Depends(get_current_user)):
    reply = await llm_client.chat(payload.message, payload.user_geo)
    return ChatResponse(conversation_id=payload.conversation_id, reply=reply)


@router.post("/chat/audio", response_model=AudioTranscriptResponse)
async def chat_audio(
    audio: UploadFile,
    conversation_id: str | None = Form(default=None),
    user_geo: str | None = Form(default=None),
    current_user: dict = Depends(get_current_user),
):
    audio_bytes = await audio.read()
    transcript = await stt_client.transcribe(
        audio_bytes, audio.filename or "audio", audio.content_type or "application/octet-stream"
    )
    return AudioTranscriptResponse(conversation_id=conversation_id, transcript=transcript)


app.include_router(router)
