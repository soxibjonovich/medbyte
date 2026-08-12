from datetime import datetime
from typing import Literal

from pydantic import BaseModel

PaymentProviderName = Literal["stripe", "payme", "uzum"]


class CheckoutRequest(BaseModel):
    appointment_id: int
    provider: PaymentProviderName


class CheckoutResponse(BaseModel):
    payment_id: int
    provider: PaymentProviderName
    checkout_url: str | None = None
    token: str | None = None


class PaymentDetail(BaseModel):
    id: int
    user_id: int
    appointment_id: int
    provider: PaymentProviderName
    external_id: str | None
    amount: int
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime
