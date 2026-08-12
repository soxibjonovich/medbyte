from contextlib import asynccontextmanager
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status

from . import consumer, database_client
from .deps import get_current_user
from .schemas import Notification, PushSubscribeRequest, PushSubscription


@asynccontextmanager
async def lifespan(_: FastAPI):
    database_client.init_client()
    await consumer.start()
    yield
    await consumer.stop()
    await database_client.close_client()


app = FastAPI(lifespan=lifespan)
router = APIRouter(prefix="/api/notifications")


@app.get("/health")
async def health():
    return {"status": "ok"}


@router.get("", response_model=list[Notification])
async def list_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    params = {"user_id": current_user["id"], "limit": limit, "offset": offset}
    return await database_client.get(f"/notifications?{urlencode(params)}")


@router.patch("/{notification_id}/read", response_model=Notification)
async def mark_notification_read(
    notification_id: int, current_user: dict = Depends(get_current_user)
):
    notification = await database_client.get_or_none(f"/notifications/{notification_id}")
    if notification is None or notification["user_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")
    return await database_client.patch(f"/notifications/{notification_id}", json={"is_read": True})


@router.post(
    "/push-subscribe", response_model=PushSubscription, status_code=status.HTTP_201_CREATED
)
async def push_subscribe(
    payload: PushSubscribeRequest, current_user: dict = Depends(get_current_user)
):
    return await database_client.post(
        "/push-subscriptions",
        json={
            "user_id": current_user["id"],
            "endpoint": payload.endpoint,
            "p256dh": payload.keys.p256dh,
            "auth_key": payload.keys.auth,
        },
    )


app.include_router(router)
