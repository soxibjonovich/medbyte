import json
import logging
import os

import aio_pika

from . import database_client, stt_client

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
STT_JOBS_QUEUE = "stt.jobs"

logger = logging.getLogger("stt_worker.consumer")

_connection: aio_pika.abc.AbstractRobustConnection | None = None


async def _handle_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    async with message.process():
        payload = json.loads(message.body)
        feedback_id = payload["feedback_id"]
        audio_file = payload["audio_file"]

        await database_client.patch(
            f"/feedback/{feedback_id}/processing", json={"processing_status": "processing"}
        )

        try:
            result = await stt_client.transcribe(audio_file)
        except Exception:
            logger.warning("stt job failed for feedback_id=%s", feedback_id, exc_info=True)
            await database_client.patch(
                f"/feedback/{feedback_id}/processing", json={"processing_status": "failed"}
            )
            return

        await database_client.patch(
            f"/feedback/{feedback_id}/processing",
            json={
                "transcript": result.get("transcript"),
                "sentiment": result.get("sentiment"),
                "keywords": result.get("keywords"),
                "processing_status": "done",
            },
        )


async def start() -> None:
    global _connection
    _connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await _connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(STT_JOBS_QUEUE, durable=True)
    await queue.consume(_handle_message)


async def stop() -> None:
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
