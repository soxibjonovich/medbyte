from contextlib import asynccontextmanager
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, FastAPI, Query

from . import database_client
from .deps import require_admin
from .schemas import (
    CreateHospital,
    Hospital,
    HospitalDetail,
    HospitalLeaderboardEntry,
    SortOption,
    UpdateHospital,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    database_client.init_client()
    yield
    await database_client.close_client()


app = FastAPI(lifespan=lifespan)
router = APIRouter(prefix="/api/hospitals")


@app.get("/health")
async def health():
    return {"status": "ok"}


@router.get("", response_model=list[Hospital])
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


@router.get("/leaderboard", response_model=list[HospitalLeaderboardEntry])
async def hospital_leaderboard(category: int | None = Query(default=None)):
    params = {"category": category} if category is not None else {}
    return await database_client.get(f"/hospitals/leaderboard?{urlencode(params)}")


@router.get("/{hospital_id}", response_model=HospitalDetail)
async def get_hospital(hospital_id: int):
    return await database_client.get(f"/hospitals/{hospital_id}")


@router.post("", response_model=Hospital, status_code=201)
async def create_hospital(payload: CreateHospital, _: dict = Depends(require_admin)):
    return await database_client.post("/hospitals", json=payload.model_dump())


@router.put("/{hospital_id}", response_model=Hospital)
async def update_hospital(
    hospital_id: int, payload: UpdateHospital, _: dict = Depends(require_admin)
):
    return await database_client.patch(
        f"/hospitals/{hospital_id}", json=payload.model_dump(exclude_unset=True)
    )


@router.delete("/{hospital_id}", status_code=204)
async def delete_hospital(hospital_id: int, _: dict = Depends(require_admin)):
    await database_client.delete(f"/hospitals/{hospital_id}")


app.include_router(router)
