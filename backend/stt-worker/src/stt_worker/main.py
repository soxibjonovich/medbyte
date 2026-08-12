import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import consumer, database_client


class HealthLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(HealthLogFilter())


@asynccontextmanager
async def lifespan(_: FastAPI):
    database_client.init_client()
    await consumer.start()
    yield
    await consumer.stop()
    await database_client.close_client()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}
