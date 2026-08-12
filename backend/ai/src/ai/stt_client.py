import asyncio
import os

import httpx
from fastapi import HTTPException

STT_BASE_URL = os.environ.get("STT_BASE_URL", "https://service.muxlisa.uz/api/v1")
STT_API_KEY = os.environ.get("STT_API_KEY", "")
STT_POLL_INTERVAL_SECONDS = float(os.environ.get("STT_POLL_INTERVAL_SECONDS", "2"))
STT_POLL_TIMEOUT_SECONDS = float(os.environ.get("STT_POLL_TIMEOUT_SECONDS", "60"))

_TIMEOUT = httpx.Timeout(30.0)


async def _to_wav(audio_bytes: bytes) -> bytes:
    """Transcode arbitrary input audio (webm/opus, mp4, ogg, ...) to 16kHz mono WAV via ffmpeg."""
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-i", "pipe:0",
        "-ar", "16000",
        "-ac", "1",
        "-f", "wav",
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    wav_bytes, stderr = await proc.communicate(input=audio_bytes)
    if proc.returncode != 0 or not wav_bytes:
        raise HTTPException(
            status_code=502, detail=f"audio conversion failed: {stderr.decode(errors='replace')[:200]}"
        )
    return wav_bytes


async def transcribe(audio_bytes: bytes, filename: str, content_type: str) -> str:
    """Submit audio to muxlisa async STT, poll until done, return transcript.
    Nothing is written to disk or persisted — audio and result live only for this request.
    """
    if not STT_API_KEY:
        raise HTTPException(status_code=502, detail="STT_API_KEY not configured")

    wav_bytes = await _to_wav(audio_bytes)
    wav_filename = os.path.splitext(filename)[0] + ".wav"
    headers = {"x-api-key": STT_API_KEY}

    async with httpx.AsyncClient(base_url=STT_BASE_URL, timeout=_TIMEOUT) as client:
        try:
            submit = await client.post(
                "/async/stt",
                headers=headers,
                files={"audio": (wav_filename, wav_bytes, "audio/wav")},
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
