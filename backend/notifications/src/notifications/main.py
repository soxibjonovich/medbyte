import os
from contextlib import asynccontextmanager
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import HTMLResponse, PlainTextResponse

from . import consumer, database_client, emailer, push
from .deps import get_current_user
from .schemas import Notification, PushSubscribeRequest, PushSubscription, TestEmailRequest


@asynccontextmanager
async def lifespan(_: FastAPI):
    database_client.init_client()
    await consumer.start()
    yield
    await consumer.stop()
    await database_client.close_client()


app = FastAPI(lifespan=lifespan)
router = APIRouter(prefix="/api/notifications")


@app.get("/health")
async def health():
    return {"status": "ok"}


@router.get("", response_model=list[Notification])
async def list_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    params = {"user_id": current_user["id"], "limit": limit, "offset": offset}
    return await database_client.get(f"/notifications?{urlencode(params)}")


@router.patch("/{notification_id}/read", response_model=Notification)
async def mark_notification_read(
    notification_id: int, current_user: dict = Depends(get_current_user)
):
    notification = await database_client.get_or_none(f"/notifications/{notification_id}")
    if notification is None or notification["user_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")
    return await database_client.patch(f"/notifications/{notification_id}", json={"is_read": True})


@router.post(
    "/push-subscribe", response_model=PushSubscription, status_code=status.HTTP_201_CREATED
)
async def push_subscribe(
    payload: PushSubscribeRequest, current_user: dict = Depends(get_current_user)
):
    return await database_client.post(
        "/push-subscriptions",
        json={
            "user_id": current_user["id"],
            "endpoint": payload.endpoint,
            "p256dh": payload.keys.p256dh,
            "auth_key": payload.keys.auth,
        },
    )


@router.post("/test-send")
async def test_send_notification(current_user: dict = Depends(get_current_user)):
    subs = await database_client.get(f"/push-subscriptions?user_id={current_user['id']}")
    payload = {
        "title": "Test notification",
        "message": "This is a test push from MedByte notifications service.",
        "url": "/notifications",
        "tag": "test",
    }
    sent = 0
    failed = 0
    for sub in subs:
        try:
            if await push.send_push(sub, payload):
                sent += 1
            else:
                failed += 1
        except push.StaleSubscription as exc:
            await database_client.delete(f"/push-subscriptions/{exc.subscription_id}")
    return {"sent": sent, "failed": failed}


@router.post("/test-email")
async def test_send_email(
    payload: TestEmailRequest = TestEmailRequest(),
    current_user: dict = Depends(get_current_user),
):
    to = payload.to or current_user.get("email")
    if not to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="no recipient: pass 'to' or set email on user profile",
        )
    sent = await emailer.send_email(to, payload.subject, payload.body)
    return {"sent": sent, "to": to}


app.include_router(router)


PUSH_SW_JS = """
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  event.waitUntil(
    self.registration.showNotification(data.title || 'push', {
      body: data.message || '',
      tag: data.tag,
      data: { url: data.url || '/' },
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url || '/'));
});
"""

PUSH_TEST_HTML = """
<!doctype html>
<html>
<head><meta charset="utf-8"><title>push test</title></head>
<body style="font-family: monospace; max-width: 640px; margin: 2em auto">
  <h2>web push test</h2>
  <p>1. paste JWT &nbsp; 2. subscribe &nbsp; 3. send test push</p>
  <textarea id="token" rows="3" style="width:100%" placeholder="JWT access token"></textarea>
  <p>
    <button id="sub">subscribe</button>
    <button id="send">send test push</button>
  </p>
  <pre id="log"></pre>
  <script>
    const VAPID_PUBLIC_KEY = "__VAPID_PUBLIC_KEY__";
    const log = (m) => (document.getElementById("log").textContent += m + "\\n");
    const token = () => document.getElementById("token").value.trim();

    function b64ToBytes(b64) {
      const pad = "=".repeat((4 - (b64.length % 4)) % 4);
      const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
      return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
    }

    document.getElementById("sub").onclick = async () => {
      try {
        const reg = await navigator.serviceWorker.register("/push-sw.js");
        const sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: b64ToBytes(VAPID_PUBLIC_KEY),
        });
        const json = sub.toJSON();
        const resp = await fetch("/api/notifications/push-subscribe", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer " + token(),
          },
          body: JSON.stringify({ endpoint: json.endpoint, keys: json.keys }),
        });
        log("subscribe: " + resp.status + " " + (await resp.text()));
      } catch (e) {
        log("subscribe error: " + e);
      }
    };

    document.getElementById("send").onclick = async () => {
      const resp = await fetch("/api/notifications/test-send", {
        method: "POST",
        headers: { Authorization: "Bearer " + token() },
      });
      log("test-send: " + resp.status + " " + (await resp.text()));
    };
  </script>
</body>
</html>
"""


@app.get("/push-test", response_class=HTMLResponse)
async def push_test_page():
    key = os.environ.get("VAPID_PUBLIC_KEY", "")
    return HTMLResponse(PUSH_TEST_HTML.replace("__VAPID_PUBLIC_KEY__", key))


@app.get("/push-sw.js", response_class=PlainTextResponse)
async def push_service_worker():
    return PlainTextResponse(PUSH_SW_JS, media_type="application/javascript")
