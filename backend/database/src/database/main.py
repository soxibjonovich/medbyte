from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud
from .schemas import CreateUserRequest, UpdateUserRequest, UserResponse
from .session import get_session, init_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    yield


app = FastAPI(root_path="/api/v1/database", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/users", response_model=list[UserResponse])
async def list_users_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await crud.list_users(session, limit=limit, offset=offset)


@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    payload: CreateUserRequest, session: AsyncSession = Depends(get_session)
):
    if payload.phone and await crud.get_user_by_phone(session, payload.phone) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="phone already registered"
        )
    if payload.email and await crud.get_user_by_email(session, payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="email already registered"
        )

    return await crud.create_user(
        session,
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        role=payload.role,
    )


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user_endpoint(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await crud.get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user


@app.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_endpoint(
    user_id: int, payload: UpdateUserRequest, session: AsyncSession = Depends(get_session)
):
    user = await crud.get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    if payload.phone and payload.phone != user.phone:
        if await crud.get_user_by_phone(session, payload.phone) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="phone already registered"
            )
    if payload.email and payload.email != user.email:
        if await crud.get_user_by_email(session, payload.email) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="email already registered"
            )

    return await crud.update_user(
        session,
        user,
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        role=payload.role,
    )


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await crud.get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    await crud.delete_user(session, user)
