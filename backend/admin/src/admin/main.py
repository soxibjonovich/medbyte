import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import jwt
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from . import database_client, rabbitmq_client, security
from .deps import require_admin, require_staff
from .schemas import (
    AuditLogEntry,
    CategoryVisitStat,
    CreateDiscount,
    CreateDoctor,
    CreateHospital,
    CreateMedicalCategory,
    CreateQueueEntry,
    CreateQuestion,
    Discount,
    Doctor,
    Hospital,
    HospitalDetail,
    MedicalCategory,
    Question,
    QueueEntry,
    SortOption,
    StatsOverview,
    UpdateDiscount,
    UpdateDoctor,
    UpdateHospital,
    UpdateMedicalCategory,
    UpdateQuestion,
)


class ConnectionManager:
    """Tracks locally-connected websocket clients and fans out broadcast messages to them."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    def connect(self, websocket: WebSocket) -> None:
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        for websocket in list(self._connections):
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(websocket)


connection_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(_: FastAPI):
    database_client.init_client()
    await rabbitmq_client.init_client()
    queue_consumer = await rabbitmq_client.consume_queue_updates(connection_manager.broadcast)
    yield
    await queue_consumer.cancel()
    await rabbitmq_client.close_client()
    await database_client.close_client()


app = FastAPI(lifespan=lifespan)

stats_router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])
hospitals_router = APIRouter(prefix="/api/hospitals", dependencies=[Depends(require_admin)])
doctors_router = APIRouter(prefix="/api/doctors", dependencies=[Depends(require_admin)])
categories_router = APIRouter(prefix="/api/categories", dependencies=[Depends(require_admin)])
discounts_router = APIRouter(prefix="/api/discounts", dependencies=[Depends(require_admin)])
queue_router = APIRouter(prefix="/api/queue", dependencies=[Depends(require_staff)])
questions_router = APIRouter(prefix="/api/admin/questions", dependencies=[Depends(require_staff)])


@app.get("/health")
async def health():
    return {"status": "ok"}


async def _log(actor: dict, action: str, entity: str, entity_id: int | None) -> None:
    await database_client.post(
        "/audit-log",
        json={"actor_id": actor["id"], "action": action, "entity": entity, "entity_id": entity_id},
    )


# --- stats & audit log -------------------------------------------------


@stats_router.get("/stats/overview", response_model=StatsOverview)
async def stats_overview():
    return await database_client.get("/stats/overview")


@stats_router.get("/stats/by-category", response_model=list[CategoryVisitStat])
async def stats_by_category(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
):
    params = {
        k: v
        for k, v in {"date_from": date_from, "date_to": date_to}.items()
        if v is not None
    }
    return await database_client.get(f"/stats/by-category?{urlencode(params)}")


@stats_router.get("/stats/export")
async def stats_export(
    format: str = Query(pattern="^(csv|pdf)$"),
    filters: str | None = Query(default=None),
):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="export not implemented yet")


@stats_router.get("/audit-log", response_model=list[AuditLogEntry])
async def audit_log(
    limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)
):
    return await database_client.get(f"/audit-log?{urlencode({'limit': limit, 'offset': offset})}")


# --- hospitals -----------------------------------------------------------


@hospitals_router.get("", response_model=list[Hospital])
async def list_hospitals(
    category: int | None = Query(default=None),
    city: str | None = Query(default=None),
    sort: SortOption | None = Query(default=None),
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    params = {
        k: v
        for k, v in {
            "category": category,
            "city": city,
            "sort": sort,
            "lat": lat,
            "lng": lng,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return await database_client.get(f"/hospitals?{urlencode(params)}")


@hospitals_router.get("/{hospital_id}", response_model=HospitalDetail)
async def get_hospital(hospital_id: int):
    return await database_client.get(f"/hospitals/{hospital_id}")


@hospitals_router.post("", response_model=Hospital, status_code=201)
async def create_hospital(payload: CreateHospital, actor: dict = Depends(require_admin)):
    hospital = await database_client.post("/hospitals", json=payload.model_dump())
    await _log(actor, "create", "hospital", hospital["id"])
    return hospital


@hospitals_router.patch("/{hospital_id}", response_model=Hospital)
async def update_hospital(
    hospital_id: int, payload: UpdateHospital, actor: dict = Depends(require_admin)
):
    hospital = await database_client.patch(
        f"/hospitals/{hospital_id}", json=payload.model_dump(exclude_unset=True)
    )
    await _log(actor, "update", "hospital", hospital_id)
    return hospital


@hospitals_router.delete("/{hospital_id}", status_code=204)
async def delete_hospital(hospital_id: int, actor: dict = Depends(require_admin)):
    await database_client.delete(f"/hospitals/{hospital_id}")
    await _log(actor, "delete", "hospital", hospital_id)


# --- doctors ---------------------------------------------------------------


@doctors_router.get("", response_model=list[Doctor])
async def list_doctors(
    hospital_id: int | None = Query(default=None),
    category: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    params = {
        k: v
        for k, v in {
            "hospital_id": hospital_id,
            "category": category,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return await database_client.get(f"/doctors?{urlencode(params)}")


@doctors_router.get("/{doctor_id}", response_model=Doctor)
async def get_doctor(doctor_id: int):
    return await database_client.get(f"/doctors/{doctor_id}")


@doctors_router.post("", response_model=Doctor, status_code=201)
async def create_doctor(payload: CreateDoctor, actor: dict = Depends(require_admin)):
    doctor = await database_client.post("/doctors", json=payload.model_dump())
    await _log(actor, "create", "doctor", doctor["id"])
    return doctor


@doctors_router.patch("/{doctor_id}", response_model=Doctor)
async def update_doctor(doctor_id: int, payload: UpdateDoctor, actor: dict = Depends(require_admin)):
    doctor = await database_client.patch(
        f"/doctors/{doctor_id}", json=payload.model_dump(exclude_unset=True)
    )
    await _log(actor, "update", "doctor", doctor_id)
    return doctor


@doctors_router.delete("/{doctor_id}", status_code=204)
async def delete_doctor(doctor_id: int, actor: dict = Depends(require_admin)):
    await database_client.delete(f"/doctors/{doctor_id}")
    await _log(actor, "delete", "doctor", doctor_id)


# --- medical categories ------------------------------------------------


@categories_router.get("", response_model=list[MedicalCategory])
async def list_categories(
    limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)
):
    return await database_client.get(
        f"/medical-categories?{urlencode({'limit': limit, 'offset': offset})}"
    )


@categories_router.get("/{category_id}", response_model=MedicalCategory)
async def get_category(category_id: int):
    return await database_client.get(f"/medical-categories/{category_id}")


@categories_router.post("", response_model=MedicalCategory, status_code=201)
async def create_category(payload: CreateMedicalCategory, actor: dict = Depends(require_admin)):
    category = await database_client.post("/medical-categories", json=payload.model_dump())
    await _log(actor, "create", "medical_category", category["id"])
    return category


@categories_router.patch("/{category_id}", response_model=MedicalCategory)
async def update_category(
    category_id: int, payload: UpdateMedicalCategory, actor: dict = Depends(require_admin)
):
    category = await database_client.patch(
        f"/medical-categories/{category_id}", json=payload.model_dump(exclude_unset=True)
    )
    await _log(actor, "update", "medical_category", category_id)
    return category


@categories_router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: int, actor: dict = Depends(require_admin)):
    await database_client.delete(f"/medical-categories/{category_id}")
    await _log(actor, "delete", "medical_category", category_id)


# --- discounts ---------------------------------------------------------


@discounts_router.get("", response_model=list[Discount])
async def list_discounts(
    user_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    params = {
        k: v
        for k, v in {"user_id": user_id, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return await database_client.get(f"/discounts?{urlencode(params)}")


@discounts_router.get("/{discount_id}", response_model=Discount)
async def get_discount(discount_id: int):
    return await database_client.get(f"/discounts/{discount_id}")


@discounts_router.post("", response_model=Discount, status_code=201)
async def create_discount(payload: CreateDiscount, actor: dict = Depends(require_admin)):
    discount = await database_client.post("/discounts", json=payload.model_dump())
    await _log(actor, "create", "discount", discount["id"])
    return discount


@discounts_router.patch("/{discount_id}", response_model=Discount)
async def update_discount(
    discount_id: int, payload: UpdateDiscount, actor: dict = Depends(require_admin)
):
    discount = await database_client.patch(
        f"/discounts/{discount_id}", json=payload.model_dump(exclude_unset=True)
    )
    await _log(actor, "update", "discount", discount_id)
    return discount


@discounts_router.delete("/{discount_id}", status_code=204)
async def delete_discount(discount_id: int, actor: dict = Depends(require_admin)):
    await database_client.delete(f"/discounts/{discount_id}")
    await _log(actor, "delete", "discount", discount_id)


# --- queue ---------------------------------------------------------------


@queue_router.get("", response_model=list[QueueEntry])
async def list_queue(
    hospital_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    params = {
        k: v
        for k, v in {"hospital_id": hospital_id, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return await database_client.get(f"/appointments?{urlencode(params)}")


@queue_router.post("", response_model=QueueEntry, status_code=201)
async def create_queue_entry(payload: CreateQueueEntry, actor: dict = Depends(require_staff)):
    entry = await database_client.post("/appointments", json=payload.model_dump())
    fire_at = datetime.fromisoformat(entry["scheduled_at"]) + timedelta(hours=2)
    delay_ms = max(0, int((fire_at - datetime.now(timezone.utc)).total_seconds() * 1000))
    try:
        await rabbitmq_client.publish_feedback_request(
            appointment_id=entry["id"],
            user_id=entry["user_id"],
            hospital_id=entry.get("hospital_id"),
            fire_at=fire_at.isoformat(),
            delay_ms=delay_ms,
        )
    except Exception:
        logging.getLogger(__name__).warning("failed to schedule feedback push", exc_info=True)
    try:
        await rabbitmq_client.publish_queue_update({"type": "queue_entry_created", "entry": entry})
    except Exception:
        logging.getLogger(__name__).warning("failed to publish queue update", exc_info=True)
    await _log(actor, "create", "queue_entry", entry["id"])
    return entry


@queue_router.post("/{appointment_id}/test-feedback-push", response_model=dict)
async def test_feedback_push(appointment_id: int, actor: dict = Depends(require_staff)):
    entry = await database_client.get_or_none(f"/appointments/{appointment_id}")
    if entry is None:
        raise HTTPException(status_code=404, detail="appointment not found")
    await rabbitmq_client.publish_feedback_request(
        appointment_id=appointment_id,
        user_id=entry["user_id"],
        hospital_id=entry.get("hospital_id"),
        fire_at=datetime.now(timezone.utc).isoformat(),
        delay_ms=1000,
    )
    await _log(actor, "test_push", "appointment", appointment_id)
    return {"scheduled": True, "appointment_id": appointment_id, "delay_ms": 1000}


# --- questions -----------------------------------------------------------


@questions_router.get("", response_model=list[Question])
async def list_questions(
    hospital_id: int = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return await database_client.get(
        f"/questions?{urlencode({'hospital_id': hospital_id, 'limit': limit, 'offset': offset})}"
    )


@questions_router.post("", response_model=Question, status_code=201)
async def create_question(payload: CreateQuestion, actor: dict = Depends(require_staff)):
    question = await database_client.post("/questions", json=payload.model_dump())
    await _log(actor, "create", "question", question["id"])
    return question


@questions_router.patch("/{question_id}", response_model=Question)
async def update_question(
    question_id: int, payload: UpdateQuestion, actor: dict = Depends(require_staff)
):
    question = await database_client.patch(
        f"/questions/{question_id}", json=payload.model_dump(exclude_unset=True)
    )
    await _log(actor, "update", "question", question_id)
    return question


@questions_router.delete("/{question_id}", status_code=204)
async def delete_question(question_id: int, actor: dict = Depends(require_staff)):
    await database_client.delete(f"/questions/{question_id}")
    await _log(actor, "delete", "question", question_id)


@app.websocket("/api/queue/ws")
async def queue_ws(websocket: WebSocket):
    """Live queue updates over a websocket, fed by rabbitmq_client.consume_queue_updates().

    Browsers can't set an Authorization header on the websocket handshake, so the JWT is
    passed as a `token` query param instead. Starlette allows sending `websocket.close`
    with a custom code while the connection is still in the CONNECTING state, so we reject
    unauthenticated/unauthorized connections before calling accept() — no need for the
    accept-then-close dance.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        user_id = security.decode_access_token(token)
    except jwt.PyJWTError:
        await websocket.close(code=4401)
        return

    user = await database_client.get_or_none(f"/users/{user_id}")
    if user is None:
        await websocket.close(code=4401)
        return
    if user["role"] not in ("staff", "admin"):
        await websocket.close(code=4403)
        return

    await websocket.accept()
    connection_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket)


app.include_router(stats_router)
app.include_router(hospitals_router)
app.include_router(doctors_router)
app.include_router(categories_router)
app.include_router(discounts_router)
app.include_router(queue_router)
app.include_router(questions_router)
