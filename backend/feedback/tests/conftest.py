from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from feedback import database_client, rabbitmq_client
from feedback import main as feedback_main
from feedback.main import app


@pytest.fixture
def patch_db(monkeypatch):
    """Replace feedback.database_client's request functions with AsyncMocks."""
    mocks = type("Mocks", (), {})()
    for name in ("get", "get_or_none", "post", "patch", "delete"):
        mock = AsyncMock()
        monkeypatch.setattr(database_client, name, mock)
        setattr(mocks, name, mock)
    return mocks


@pytest.fixture
def patch_rabbitmq(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(rabbitmq_client, "publish_stt_job", mock)
    return mock


@pytest.fixture(autouse=True)
def audio_storage_dir(monkeypatch, tmp_path):
    """Redirect audio uploads to a temp dir — lifespan (which mkdirs it) never runs under ASGITransport."""
    monkeypatch.setattr(feedback_main, "AUDIO_STORAGE_DIR", tmp_path)
    return tmp_path


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
