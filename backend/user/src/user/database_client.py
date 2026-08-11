import os

import httpx
from fastapi import HTTPException

DATABASE_SERVICE_URL = os.environ.get("DATABASE_SERVICE_URL", "http://localhost:8005")

_TIMEOUT = httpx.Timeout(10.0)
_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)

_client: httpx.AsyncClient | None = None


def init_client() -> None:
    """Create the shared, connection-pooled client. Call once on app startup."""
    global _client
    _client = httpx.AsyncClient(base_url=DATABASE_SERVICE_URL, timeout=_TIMEOUT, limits=_LIMITS)


async def close_client() -> None:
    """Release pooled connections. Call once on app shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _get_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("Database client not initialized — call init_client() on app startup")
    return _client


async def request(method: str, path: str, **kwargs) -> dict | list | None:
    try:
        response = await _get_client().request(method, path, **kwargs)
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="database service unavailable")

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        raise HTTPException(status_code=response.status_code, detail=detail or "database service error")

    if not response.content:
        return None
    return response.json()


async def get(path: str) -> dict | list:
    return await request("GET", path)


async def get_or_none(path: str) -> dict | None:
    try:
        return await request("GET", path)
    except HTTPException as exc:
        if exc.status_code == 404:
            return None
        raise


async def post(path: str, json: dict | None = None) -> dict | list:
    return await request("POST", path, json=json)


async def patch(path: str, json: dict | None = None) -> dict | list:
    return await request("PATCH", path, json=json)


async def delete(path: str) -> None:
    await request("DELETE", path)
