from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter, Depends

from . import database_client, schemas
from .deps import get_current_user


@asynccontextmanager
async def lifespan(_: FastAPI):
    database_client.init_client()
    yield
    await database_client.close_client()

app = FastAPI(lifespan=lifespan)
router = APIRouter(prefix="/api/v1/user")

@router.get("/health", response_model=dict)
async def health():
    return {"status": "ok"}


@router.get("/me", response_model=schemas.User)
async def get_user(
        user: schemas.User = Depends(get_current_user)
):
    return user


@router.patch("/me", response_model=schemas.User)
async def update_user(
        payload: schemas.UpdateUser,
        user: schemas.User = Depends(get_current_user),
):
    updated = await database_client.patch(
        f"/users/{user.id}", json=payload.model_dump(exclude_unset=True)
    )
    return schemas.User(**updated)


@router.get("/me/appointments", response_model=list[schemas.Appointment])
async def get_user_appointments(
        user: schemas.User = Depends(get_current_user)
):
    return await database_client.get(f"/appointments?user_id={user.id}")


@router.get("/me/notifications", response_model=list[schemas.Notification])
async def get_user_notifications(
        user: schemas.User = Depends(get_current_user)
):
    return await database_client.get(f"/notifications?user_id={user.id}")


@router.get("/me/discounts", response_model=list[schemas.Discount])
async def get_user_discounts(
        user: schemas.User = Depends(get_current_user)
):
    return await database_client.get(f"/discounts?user_id={user.id}")


app.include_router(router)