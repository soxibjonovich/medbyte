import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse

from . import database_client, google_auth, rate_limit, schemas, security
from .deps import get_current_user


class HealthLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(HealthLogFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    database_client.init_client()
    rate_limit.init_client()
    yield
    await rate_limit.close_client()
    await database_client.close_client()


app = FastAPI(lifespan=lifespan)
router = APIRouter(prefix="/api/v1/auth")


@app.get("/health")
async def health():
    return {"status": "ok"}


@router.post(
    "/register",
    response_model=schemas.TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit.rate_limit_dependency("register", limit=5, window_seconds=60))],
)
async def register_new_user(user: schemas.CreateUser):
    password_hash = security.hash_password(user.password)
    new_user = await database_client.post(
        "/users",
        json={
            "full_name": user.full_name,
            "username": user.username,
            "phone": user.phone,
            "email": user.email,
            "password_hash": password_hash,
        },
    )

    token = security.create_access_token(new_user["id"])
    return schemas.TokenResponse(
        access_token=token, user=schemas.UserResponse.model_validate(new_user)
    )


@router.post(
    "/login",
    response_model=schemas.TokenResponse,
    dependencies=[Depends(rate_limit.rate_limit_dependency("login", limit=10, window_seconds=60))],
)
async def login_user(credentials: schemas.LoginUser):
    # Per-IP limiting (above) stops a single attacker hammering the endpoint;
    # this per-username check additionally stops distributed brute-force
    # (many IPs) targeting one account. Identifier comes from the parsed
    # body, so it can't be expressed as a generic Depends() on Request alone.
    if not await rate_limit.is_allowed("login_user", credentials.username, limit=5, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate limit exceeded, try again shortly",
            headers={"Retry-After": "60"},
        )

    record = await database_client.get_or_none(f"/users/by-username/{credentials.username}")
    if (
        record is None
        or record["password_hash"] is None
        or not security.verify_password(credentials.password, record["password_hash"])
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid username or password"
        )

    token = security.create_access_token(record["id"])
    return schemas.TokenResponse(
        access_token=token, user=schemas.UserResponse.model_validate(record)
    )


@router.get("/me", response_model=schemas.UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return schemas.UserResponse.model_validate(current_user)


@router.get("/google/test", response_class=HTMLResponse, include_in_schema=False)
async def google_login_test_page():
    """Manual browser test page for the Google sign-in redirect flow. Dev-only."""
    configured = google_auth.is_configured()
    button = (
        '<a href="/api/v1/auth/google/login"><button type="button">Sign in with Google</button></a>'
        if configured
        else "<p>Google OAuth is not configured (missing GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI).</p>"
    )
    return f"""<!doctype html>
<html>
<head><title>anonfeedback auth - Google sign-in test</title></head>
<body>
<h1>Google sign-in test</h1>
{button}
</body>
</html>"""


@router.get("/google/login")
async def google_login():
    if not google_auth.is_configured():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="google oauth not configured",
        )
    return RedirectResponse(google_auth.build_authorization_url())


@router.get("/callback", response_model=schemas.TokenResponse)
async def google_callback(code: str, state: str):
    if not google_auth.verify_state(state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid state")

    token_data = await google_auth.exchange_code(code)
    claims = google_auth.verify_id_token(token_data["id_token"])

    if not claims.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="google email not verified"
        )

    email = claims["email"]
    user = await database_client.get_or_none(f"/users/by-email/{email}")
    if user is None:
        user = await database_client.post(
            "/users",
            json={
                "full_name": claims.get("name", email),
                "phone": None,
                "email": email,
                "password_hash": None,
            },
        )

    token = security.create_access_token(user["id"])
    return schemas.TokenResponse(
        access_token=token, user=schemas.UserResponse.model_validate(user)
    )


app.include_router(router)
