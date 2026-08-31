from pydantic import BaseModel
from decimal import Decimal

from app.models.provider_payment import PaymentStatus
from app.schemas.scenarios import PaymentScenario

class CreatePaymentRequest(BaseModel):
    gateway_payment_id: str
    amount: Decimal
    currency: str
    scenario: PaymentScenario = PaymentScenario.SUCCESS

class ProviderPaymentResponse(BaseModel):
    provider_payment_id: str
    gateway_payment_id: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    failure_reason: str | None = None

    model_config = {
        "from_attributes": True
    }
