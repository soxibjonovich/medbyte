from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from admin import database_client, rabbitmq_client
from admin.main import app


@pytest.fixture
def patch_db(monkeypatch):
    """Replace admin.database_client's request functions with AsyncMocks."""
    mocks = type("Mocks", (), {})()
    for name in ("get", "get_or_none", "post", "patch", "delete"):
        mock = AsyncMock()
        monkeypatch.setattr(database_client, name, mock)
        setattr(mocks, name, mock)
    return mocks


@pytest.fixture
def patch_rabbitmq(monkeypatch):
    """Replace admin.rabbitmq_client's publish functions with AsyncMocks."""
    mocks = type("Mocks", (), {})()
    for name in ("publish_feedback_request", "publish_queue_update"):
        mock = AsyncMock()
        monkeypatch.setattr(rabbitmq_client, name, mock)
        setattr(mocks, name, mock)
    return mocks


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
