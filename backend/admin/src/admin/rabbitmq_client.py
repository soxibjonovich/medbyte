import json
import logging
import os

import aio_pika

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
DELAYED_EXCHANGE = "notifications.delayed"
FEEDBACK_ROUTING_KEY = "feedback.request"
QUEUE_UPDATES_EXCHANGE = "queue.updates"

_logger = logging.getLogger(__name__)

_connection: aio_pika.abc.AbstractRobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None
_exchanges: dict[str, aio_pika.abc.AbstractExchange] = {}


async def init_client() -> None:
    """Connect and declare the exchanges. Call once on app startup."""
    global _connection, _channel
    _connection = await aio_pika.connect_robust(RABBITMQ_URL)
    _channel = await _connection.channel()
    _exchanges[DELAYED_EXCHANGE] = await _channel.declare_exchange(
        DELAYED_EXCHANGE,
        aio_pika.ExchangeType.X_DELAYED_MESSAGE,
        durable=True,
        arguments={"x-delayed-type": "direct"},
    )
    _exchanges[QUEUE_UPDATES_EXCHANGE] = await _channel.declare_exchange(
        QUEUE_UPDATES_EXCHANGE,
        aio_pika.ExchangeType.FANOUT,
        durable=True,
    )


async def close_client() -> None:
    """Call once on app shutdown."""
    global _connection, _channel
    if _connection is not None:
        await _connection.close()
        _connection = None
        _channel = None
        _exchanges.clear()


async def publish_feedback_request(
    appointment_id: int, user_id: int, hospital_id: int | None, fire_at: str, delay_ms: int
) -> None:
    if _channel is None:
        raise RuntimeError("RabbitMQ client not initialized — call init_client() on app startup")
    body = json.dumps(
        {
            "appointment_id": appointment_id,
            "user_id": user_id,
            "hospital_id": hospital_id,
            "fire_at": fire_at,
        }
    ).encode()
    message = aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
    message.headers = {"x-delay": delay_ms}
    await _channel.basic_publish(message, routing_key=FEEDBACK_ROUTING_KEY, exchange=DELAYED_EXCHANGE)


async def publish_queue_update(event: dict) -> None:
    """Publish a live queue event to the queue.updates fanout exchange."""
    exchange = _exchanges.get(QUEUE_UPDATES_EXCHANGE)
    if exchange is None:
        raise RuntimeError("RabbitMQ client not initialized — call init_client() on app startup")
    body = json.dumps(event).encode()
    message = aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
    await exchange.publish(message, routing_key="")


class QueueConsumer:
    """Handle for a running consume_queue_updates() subscription; call cancel() on shutdown."""

    def __init__(self, queue: aio_pika.abc.AbstractQueue, consumer_tag: str) -> None:
        self._queue = queue
        self._consumer_tag = consumer_tag

    async def cancel(self) -> None:
        await self._queue.cancel(self._consumer_tag)


async def consume_queue_updates(callback) -> QueueConsumer:
    """Declare a server-named, exclusive, auto-delete queue bound to queue.updates and
    consume it in the background, invoking `await callback(event_dict)` per message.

    Every running admin replica calls this once, so every replica gets its own copy of
    every event (fanout + exclusive queue) and can broadcast to its own locally-connected
    websocket clients.

    Returns a QueueConsumer handle that can be cancelled cleanly on shutdown. Note the
    exclusive/auto-delete queue is torn down automatically if the connection is closed
    without calling cancel() first, so leaking this is not a real risk either way.
    """
    if _channel is None or QUEUE_UPDATES_EXCHANGE not in _exchanges:
        raise RuntimeError("RabbitMQ client not initialized — call init_client() on app startup")

    queue = await _channel.declare_queue(exclusive=True, auto_delete=True)
    await queue.bind(_exchanges[QUEUE_UPDATES_EXCHANGE], routing_key="")

    async def _on_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
        async with message.process():
            try:
                await callback(json.loads(message.body))
            except Exception:
                _logger.warning("queue update callback failed", exc_info=True)

    consumer_tag = await queue.consume(_on_message)
    return QueueConsumer(queue, consumer_tag)
