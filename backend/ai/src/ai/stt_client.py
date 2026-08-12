import asyncio
import os

import httpx
from fastapi import HTTPException

STT_BASE_URL = os.environ.get("STT_BASE_URL", "https://service.muxlisa.uz/api/v1")
STT_API_KEY = os.environ.get("STT_API_KEY", "")
STT_POLL_INTERVAL_SECONDS = float(os.environ.get("STT_POLL_INTERVAL_SECONDS", "2"))
STT_POLL_TIMEOUT_SECONDS = float(os.environ.get("STT_POLL_TIMEOUT_SECONDS", "60"))

_TIMEOUT = httpx.Timeout(30.0)


async def transcribe(audio_bytes: bytes, filename: str, content_type: str) -> str:
    """Submit audio to muxlisa async STT, poll until done, return transcript.
    Nothing is written to disk or persisted — audio and result live only for this request.
    """
    if not STT_API_KEY:
        raise HTTPException(status_code=502, detail="STT_API_KEY not configured")

    headers = {"x-api-key": STT_API_KEY}

    async with httpx.AsyncClient(base_url=STT_BASE_URL, timeout=_TIMEOUT) as client:
        try:
            submit = await client.post(
                "/async/stt",
                headers=headers,
                files={"audio": (filename, audio_bytes, content_type)},
            )
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="STT service unavailable")

        if submit.status_code >= 400:
            raise HTTPException(status_code=502, detail="STT service rejected audio")

        task_id = submit.json()["task_id"]

        elapsed = 0.0
        while elapsed < STT_POLL_TIMEOUT_SECONDS:
            await asyncio.sleep(STT_POLL_INTERVAL_SECONDS)
            elapsed += STT_POLL_INTERVAL_SECONDS

            try:
                poll = await client.get(f"/async/stt/status/{task_id}", headers=headers)
            except httpx.HTTPError:
                raise HTTPException(status_code=502, detail="STT service unavailable")

            if poll.status_code >= 400:
                raise HTTPException(status_code=502, detail="STT service error")

            body = poll.json()
            if body["status"] == "COMPLETED":
                return body["result"]
            if body["status"] == "FAILED":
                raise HTTPException(status_code=502, detail="STT transcription failed")

    raise HTTPException(status_code=504, detail="STT transcription timed out")
