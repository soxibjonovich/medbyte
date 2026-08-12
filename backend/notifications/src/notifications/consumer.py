import json
import logging
import os

import aio_pika

from . import database_client, emailer

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
DELAYED_EXCHANGE = "notifications.delayed"
FEEDBACK_QUEUE = "feedback.request"
FEEDBACK_ROUTING_KEY = "feedback.request"

logger = logging.getLogger("notifications.consumer")

_connection: aio_pika.abc.AbstractRobustConnection | None = None


async def _handle_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    async with message.process():
        try:
            body = json.loads(message.body)
            appointment_id = body["appointment_id"]
            user_id = body["user_id"]

            user = await database_client.get_or_none(f"/users/{user_id}")
            email = (user or {}).get("email")
            if not email:
                logger.info("user %s has no email; skipping feedback reminder", user_id)
                return

            await emailer.send_email(
                to=email,
                subject="Share your feedback",
                body=(
                    "Tell us about your recent visit.\n\n"
                    f"Rate your experience here: /feedback/{appointment_id}\n\n"
                    "Thank you for helping other patients choose the right doctor."
                ),
            )
        except Exception:
            logger.warning("failed to handle message", exc_info=True)


async def start() -> None:
    global _connection
    _connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await _connection.channel()
    await channel.set_qos(prefetch_count=1)
    exchange = await channel.declare_exchange(
        DELAYED_EXCHANGE,
        aio_pika.ExchangeType.X_DELAYED_MESSAGE,
        durable=True,
        arguments={"x-delayed-type": "direct"},
    )
    queue = await channel.declare_queue(FEEDBACK_QUEUE, durable=True)
    await queue.bind(exchange=exchange, routing_key=FEEDBACK_ROUTING_KEY)
    await queue.consume(_handle_message)


async def stop() -> None:
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
