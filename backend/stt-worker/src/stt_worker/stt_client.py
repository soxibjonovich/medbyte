import os

import httpx

STT_API_URL = os.environ.get("STT_API_URL")
_TIMEOUT = httpx.Timeout(60.0)


async def transcribe(audio_path: str) -> dict:
    """POST audio to the external STT API. Contract (see README): returns
    {"transcript": str, "sentiment": "positive"|"neutral"|"negative", "keywords": [str]}.
    """
    if not STT_API_URL:
        raise RuntimeError("STT_API_URL not configured")

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        with open(audio_path, "rb") as audio_fh:
            response = await client.post(
                f"{STT_API_URL}/transcribe",
                files={"audio": audio_fh},
            )
        response.raise_for_status()
        return response.json()
