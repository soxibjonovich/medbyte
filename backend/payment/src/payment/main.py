import logging
import os
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse

from . import database_client, rabbitmq_client
from .deps import get_current_user
from .schemas import CheckoutRequest, CheckoutResponse, PaymentDetail

DEMO_AMOUNT = int(os.environ.get("PAYMENT_DEMO_AMOUNT", "2000"))


class HealthLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(HealthLogFilter())
DEMO_CURRENCY = os.environ.get("PAYMENT_DEMO_CURRENCY", "usd")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://192.168.0.101:5173")
PAYMENT_SUCCESS_URL = "http://192.168.0.101:8010/api/payments/success"

logger = logging.getLogger("payment.main")


async def _finalize_paid_payment(payment_id: int) -> None:
    """Mark a payment paid and assign the appointment's queue number (idempotent)."""
    payment = await database_client.get(f"/payments/{payment_id}")
    if payment.get("status") == "paid":
        await database_client.post(f"/appointments/{payment['appointment_id']}/assign-queue")

        # Best-effort: mint a one-time feedback link and email it instantly. Never
        # fail the webhook over this — the payment itself already succeeded.
        try:
            token_record = await database_client.post(
                "/feedback-tokens",
                json={
                    "appointment_id": payment["appointment_id"],
                    "user_id": payment["user_id"],
                },
            )
            await rabbitmq_client.publish_feedback_link_email(
                payment["user_id"], payment["appointment_id"], token_record["token"]
            )
        except Exception:
            logger.warning(
                "failed to mint/publish feedback link for payment_id=%s", payment_id, exc_info=True
            )


@asynccontextmanager
async def lifespan(_: FastAPI):
    database_client.init_client()
    await rabbitmq_client.init_client()
    yield
    await rabbitmq_client.close_client()
    await database_client.close_client()


app = FastAPI(lifespan=lifespan)
router = APIRouter(prefix="/api/payments")


@app.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(payload: CheckoutRequest, current_user: dict = Depends(get_current_user)):
    appointment = await database_client.get_or_none(f"/appointments/{payload.appointment_id}")
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="appointment not found")
    if appointment["user_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not your appointment")

    payment = await database_client.post(
        "/payments",
        json={
            "user_id": current_user["id"],
            "appointment_id": payload.appointment_id,
            "provider": payload.provider,
            "amount": DEMO_AMOUNT,
            "currency": DEMO_CURRENCY,
        },
    )

    if payload.provider == "stripe":
        # Stripe gateway removed — always succeed instantly (demo mode).
        external_id = f"demo-{payment['id']}"
        await database_client.patch(
            f"/payments/{payment['id']}", json={"external_id": external_id, "status": "paid"}
        )
        await _finalize_paid_payment(payment["id"])
        return CheckoutResponse(
            payment_id=payment["id"],
            provider="stripe",
            checkout_url=f"{PAYMENT_SUCCESS_URL}?session_id={external_id}",
        )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"{payload.provider} checkout not implemented in this demo",
    )


@router.post("/webhook/payme", include_in_schema=False)
async def payme_webhook():
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Payme integration not implemented in this demo",
    )


@router.get("/success", include_in_schema=False)
async def payment_success(session_id: str = ""):
    payment = await database_client.get_or_none(f"/payments/by-external/{session_id}")
    if payment is not None and payment.get("status") == "paid":
        await _finalize_paid_payment(payment["id"])
    return RedirectResponse(f"{FRONTEND_URL}/payment/success?session_id={session_id}")


@router.get("/cancel", include_in_schema=False)
async def payment_cancel():
    return RedirectResponse(f"{FRONTEND_URL}/payment/cancelled")


@router.get("/by-session/{session_id}", response_model=PaymentDetail)
async def get_payment_by_session(session_id: str, current_user: dict = Depends(get_current_user)):
    payment = await database_client.get_or_none(f"/payments/by-external/{session_id}")
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment not found")
    if payment["user_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not your payment")
    return payment


@router.post("/webhook/uzum", include_in_schema=False)
async def uzum_webhook():
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Uzum Bank integration not implemented in this demo",
    )


@router.get("/{payment_id}", response_model=PaymentDetail)
async def get_payment(payment_id: int, current_user: dict = Depends(get_current_user)):
    payment = await database_client.get_or_none(f"/payments/{payment_id}")
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment not found")
    if payment["user_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not your payment")
    return payment


app.include_router(router)
