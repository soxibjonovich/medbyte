import os
from contextlib import asynccontextmanager

import stripe
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status

from . import database_client, stripe_client
from .deps import get_current_user
from .schemas import CheckoutRequest, CheckoutResponse, PaymentDetail

DEMO_AMOUNT = int(os.environ.get("PAYMENT_DEMO_AMOUNT", "2000"))
DEMO_CURRENCY = os.environ.get("PAYMENT_DEMO_CURRENCY", "usd")


@asynccontextmanager
async def lifespan(_: FastAPI):
    database_client.init_client()
    yield
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
        try:
            session = stripe_client.create_checkout_session(
                payment["id"], DEMO_AMOUNT, DEMO_CURRENCY
            )
        except stripe.StripeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=f"stripe error: {exc.user_message or str(exc)}"
            )
        await database_client.patch(f"/payments/{payment['id']}", json={"external_id": session.id})
        return CheckoutResponse(payment_id=payment["id"], provider="stripe", checkout_url=session.url)

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"{payload.provider} checkout not implemented in this demo",
    )


@router.post("/webhook/stripe", include_in_schema=False)
async def stripe_webhook(request: Request):
    raw_body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe_client.construct_event(raw_body, sig_header)
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid signature")

    event_type = event["type"]
    session = event["data"]["object"]
    payment_id = session.get("metadata", {}).get("payment_id")

    if payment_id is not None:
        if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            await database_client.patch(
                f"/payments/{payment_id}", json={"external_id": session["id"], "status": "paid"}
            )
        elif event_type in ("checkout.session.expired", "checkout.session.async_payment_failed"):
            await database_client.patch(f"/payments/{payment_id}", json={"status": "failed"})

    return {"received": True}


@router.post("/webhook/payme", include_in_schema=False)
async def payme_webhook():
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Payme integration not implemented in this demo",
    )


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
