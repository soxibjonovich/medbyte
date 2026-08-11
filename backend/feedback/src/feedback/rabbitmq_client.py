import json
import os

import aio_pika

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
STT_JOBS_QUEUE = "stt.jobs"

_connection: aio_pika.abc.AbstractRobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None


async def init_client() -> None:
    """Connect and declare the durable STT job queue. Call once on app startup."""
    global _connection, _channel
    _connection = await aio_pika.connect_robust(RABBITMQ_URL)
    _channel = await _connection.channel()
    await _channel.declare_queue(STT_JOBS_QUEUE, durable=True)


async def close_client() -> None:
    """Call once on app shutdown."""
    global _connection, _channel
    if _connection is not None:
        await _connection.close()
        _connection = None
        _channel = None


async def publish_stt_job(feedback_id: int, audio_file: str) -> None:
    if _channel is None:
        raise RuntimeError("RabbitMQ client not initialized — call init_client() on app startup")
    body = json.dumps({"feedback_id": feedback_id, "audio_file": audio_file}).encode()
    await _channel.default_exchange.publish(
        aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key=STT_JOBS_QUEUE,
    )
