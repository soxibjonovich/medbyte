import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

# SQLite has no ARRAY/JSONB types. Compile both as JSON for DDL, and patch
# the postgres ARRAY type's bind/result processors to (de)serialize via
# json for the sqlite dialect specifically — JSONB already round-trips
# through plain json under sqlite without a processor patch.


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(element, compiler, **kw):
    return "JSON"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


_orig_array_bind = ARRAY.bind_processor
_orig_array_result = ARRAY.result_processor


def _array_bind_processor(self, dialect):
    if dialect.name == "sqlite":
        def process(value):
            return None if value is None else json.dumps(value)

        return process
    return _orig_array_bind(self, dialect)


def _array_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            return None if value is None else json.loads(value)

        return process
    return _orig_array_result(self, dialect, coltype)


ARRAY.bind_processor = _array_bind_processor
ARRAY.result_processor = _array_result_processor

from database.models import Base  # noqa: E402
from database.session import get_session  # noqa: E402
from database.main import app  # noqa: E402


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(session):
    async def _override_get_session():
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
