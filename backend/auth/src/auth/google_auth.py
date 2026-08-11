import os
import secrets
from typing import Any, Mapping
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

load_dotenv()

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

_pending_states: set[str] = set()
_google_request = google_requests.Request()


def is_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI)


def build_authorization_url() -> str:
    state = secrets.token_urlsafe(24)
    _pending_states.add(state)
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def verify_state(state: str) -> bool:
    try:
        _pending_states.remove(state)
        return True
    except KeyError:
        return False


async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return resp.json()


def verify_id_token(id_token_jwt: str) -> Mapping[str, Any]:
    """Verify signature, issuer, audience, expiry against Google's live JWKS."""
    return google_id_token.verify_oauth2_token(
        id_token_jwt, _google_request, audience=GOOGLE_CLIENT_ID
    )
