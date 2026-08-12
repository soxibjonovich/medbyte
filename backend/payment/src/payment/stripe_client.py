import os

import stripe

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
SUCCESS_URL = os.environ.get(
    "PAYMENT_SUCCESS_URL", "http://localhost:8010/api/payments/success"
)
CANCEL_URL = os.environ.get("PAYMENT_CANCEL_URL", "http://localhost:8010/api/payments/cancel")


def create_checkout_session(payment_id: int, amount: int, currency: str) -> stripe.checkout.Session:
    return stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": currency,
                    "product_data": {"name": f"Appointment payment #{payment_id}"},
                    "unit_amount": amount,
                },
                "quantity": 1,
            }
        ],
        metadata={"payment_id": str(payment_id)},
        success_url=f"{SUCCESS_URL}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=CANCEL_URL,
    )


def construct_event(payload: bytes, sig_header: str) -> stripe.Event:
    return stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
