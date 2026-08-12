import json
import logging
import os

from pywebpush import WebPushException, webpush

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:admin@example.com")
PUSH_TTL_SECONDS = int(os.environ.get("PUSH_TTL_SECONDS", "86400"))

logger = logging.getLogger("notifications.push")


class StaleSubscription(Exception):
    def __init__(self, subscription_id):
        super().__init__(f"stale push subscription: {subscription_id}")
        self.subscription_id = subscription_id


async def send_push(subscription: dict, payload: dict) -> bool:
    if not VAPID_PRIVATE_KEY:
        logger.warning("VAPID_PRIVATE_KEY not set, skipping push")
        return False

    sub_info = {
        "endpoint": subscription["endpoint"],
        "keys": {"p256dh": subscription["p256dh"], "auth": subscription["auth_key"]},
    }
    try:
        webpush(
            subscription_info=sub_info,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_SUBJECT},
            ttl=PUSH_TTL_SECONDS,
        )
    except WebPushException as exc:
        if exc.response is not None and exc.response.status_code in (404, 410):
            raise StaleSubscription(subscription["id"]) from exc
        logger.warning("push failed for subscription %s", subscription.get("id"), exc_info=True)
        return False
    return True
