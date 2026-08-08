from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import Currency, PaymentStatus


class CreatePaymentRequest(BaseModel):
    merchant_payment_method_id: UUID
    amount: int = Field(..., gt=0)
    currency: Currency
    payment_metadata: dict = Field(default_factory=dict)
    idempotency_key: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )


class CreatePaymentResponse(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)