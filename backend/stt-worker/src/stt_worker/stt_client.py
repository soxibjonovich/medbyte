import asyncio
import os

import httpx

STT_BASE_URL = os.environ.get("STT_BASE_URL", "https://service.muxlisa.uz/api/v1")
STT_API_KEY = os.environ.get("STT_API_KEY", "")
STT_POLL_INTERVAL_SECONDS = float(os.environ.get("STT_POLL_INTERVAL_SECONDS", "2"))
STT_POLL_TIMEOUT_SECONDS = float(os.environ.get("STT_POLL_TIMEOUT_SECONDS", "60"))

_TIMEOUT = httpx.Timeout(30.0)


async def transcribe(audio_path: str) -> str:
    """Read audio file, submit to muxlisa async STT, poll until done, return transcript."""
    if not STT_API_KEY:
        raise RuntimeError("STT_API_KEY not configured")

    with open(audio_path, "rb") as audio_fh:
        audio_bytes = audio_fh.read()

    headers = {"x-api-key": STT_API_KEY}

    async with httpx.AsyncClient(base_url=STT_BASE_URL, timeout=_TIMEOUT) as client:
        try:
            submit = await client.post(
                "/async/stt",
                headers=headers,
                files={"audio": (os.path.basename(audio_path), audio_bytes)},
            )
        except httpx.HTTPError:
            raise RuntimeError("STT service unavailable")

        if submit.status_code >= 400:
            raise RuntimeError("STT service rejected audio")

        task_id = submit.json()["task_id"]

        elapsed = 0.0
        while elapsed < STT_POLL_TIMEOUT_SECONDS:
            await asyncio.sleep(STT_POLL_INTERVAL_SECONDS)
            elapsed += STT_POLL_INTERVAL_SECONDS
            try:
                poll = await client.get(f"/async/stt/status/{task_id}", headers=headers)
            except httpx.HTTPError:
                raise RuntimeError("STT service unavailable")
            if poll.status_code >= 400:
                raise RuntimeError("STT service error")
            body = poll.json()
            if body["status"] == "COMPLETED":
                return body["result"]
            if body["status"] == "FAILED":
                raise RuntimeError("STT transcription failed")

    raise TimeoutError("STT transcription timed out")
