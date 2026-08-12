import asyncio
import os

import httpx

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
        raise RuntimeError(f"audio conversion failed: {stderr.decode(errors='replace')[:200]}")
    return wav_bytes


async def transcribe(audio_path: str) -> str:
    """Read audio file, submit to muxlisa async STT, poll until done, return transcript."""
    if not STT_API_KEY:
        raise RuntimeError("STT_API_KEY not configured")

    with open(audio_path, "rb") as audio_fh:
        audio_bytes = audio_fh.read()

    wav_bytes = await _to_wav(audio_bytes)
    wav_filename = os.path.splitext(os.path.basename(audio_path))[0] + ".wav"
    headers = {"x-api-key": STT_API_KEY}

    async with httpx.AsyncClient(base_url=STT_BASE_URL, timeout=_TIMEOUT) as client:
        try:
            submit = await client.post(
                "/async/stt",
                headers=headers,
                files={"audio": (wav_filename, wav_bytes, "audio/wav")},
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
