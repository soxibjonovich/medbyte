from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import consumer, database_client


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
