from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import User, get_session

from . import google_auth, repository, schemas, security
from .deps import get_current_user

app = FastAPI()
router = APIRouter(prefix="/api/v1/auth")


@app.get("/health")
async def health():
    return {"status": "ok"}


@router.post(
    "/register",
    response_model=schemas.TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_new_user(
    user: schemas.CreateUser, session: AsyncSession = Depends(get_session)
):
    if await repository.get_by_phone(session, user.phone) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="phone already registered"
        )
    if user.email and await repository.get_by_email(session, user.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="email already registered"
        )

    password_hash = security.hash_password(user.password)
    new_user = await repository.create_user(
        session,
        full_name=user.full_name,
        phone=user.phone,
        email=user.email,
        password_hash=password_hash,
    )

    token = security.create_access_token(new_user.id)
    return schemas.TokenResponse(
        access_token=token, user=schemas.UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=schemas.TokenResponse)
async def login_user(
    credentials: schemas.LoginUser, session: AsyncSession = Depends(get_session)
):
    record = await repository.get_by_phone(session, credentials.phone)
    if (
        record is None
        or record.password_hash is None
        or not security.verify_password(credentials.password, record.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid phone or password"
        )

    token = security.create_access_token(record.id)
    return schemas.TokenResponse(
        access_token=token, user=schemas.UserResponse.model_validate(record)
    )


@router.get("/me", response_model=schemas.UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
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
async def google_callback(
    code: str, state: str, session: AsyncSession = Depends(get_session)
):
    if not google_auth.verify_state(state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid state")

    token_data = await google_auth.exchange_code(code)
    claims = google_auth.verify_id_token(token_data["id_token"])

    if not claims.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="google email not verified"
        )

    email = claims["email"]
    user = await repository.get_by_email(session, email)
    if user is None:
        user = await repository.create_user(
            session,
            full_name=claims.get("name", email),
            phone=None,
            email=email,
            password_hash=None,
        )

    token = security.create_access_token(user.id)
    return schemas.TokenResponse(
        access_token=token, user=schemas.UserResponse.model_validate(user)
    )


app.include_router(router)
