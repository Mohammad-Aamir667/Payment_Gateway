from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, status

from app.common.enums import PaymentStatus
from app.merchant_credentials.dependencies import get_authenticated_merchant
from app.payment.schemas import (
    CreatePaymentRequest,
    CreatePaymentResponse,
)

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CreatePaymentResponse,
)
async def create_payment(
    request: CreatePaymentRequest,api_key: str = Depends(get_authenticated_merchant),
) -> CreatePaymentResponse:
    return CreatePaymentResponse(
        payment_id=uuid4(),
        status=PaymentStatus.PROCESSING,
        created_at=datetime.now(timezone.utc),
    )