import json
import os

import aio_pika

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
FEEDBACK_LINK_EMAIL_QUEUE = "feedback.link.email"

_connection: aio_pika.abc.AbstractRobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None


async def init_client() -> None:
    """Connect and declare the durable feedback-link-email queue. Call once on app startup."""
    global _connection, _channel
    _connection = await aio_pika.connect_robust(RABBITMQ_URL)
    _channel = await _connection.channel()
    await _channel.declare_queue(FEEDBACK_LINK_EMAIL_QUEUE, durable=True)


async def close_client() -> None:
    """Call once on app shutdown."""
    global _connection, _channel
    if _connection is not None:
        await _connection.close()
        _connection = None
        _channel = None


async def publish_feedback_link_email(user_id: int, appointment_id: int, token: str) -> None:
    if _channel is None:
        raise RuntimeError("RabbitMQ client not initialized — call init_client() on app startup")
    body = json.dumps(
        {"user_id": user_id, "appointment_id": appointment_id, "token": token}
    ).encode()
    await _channel.default_exchange.publish(
        aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key=FEEDBACK_LINK_EMAIL_QUEUE,
    )
