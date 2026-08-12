import os

import httpx
from fastapi import HTTPException

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://172.16.8.197:1234/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "lm-studio")

_TIMEOUT = httpx.Timeout(60.0)

SYSTEM_PROMPT = (
    "You are a medical triage assistant for a hospital feedback platform. "
    "Given a patient's message, suggest which kind of doctor/specialist they should see "
    "and why. Be concise."
)


async def chat(message: str, user_geo: str | None = None) -> str:
    user_content = message if not user_geo else f"[patient location: {user_geo}]\n{message}"

    async with httpx.AsyncClient(base_url=LLM_BASE_URL, timeout=_TIMEOUT) as client:
        try:
            response = await client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.3,
                },
            )
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="LLM service unavailable")

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="LLM service error")

    data = response.json()
    return data["choices"][0]["message"]["content"]
