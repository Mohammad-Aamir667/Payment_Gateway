from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.merchant_credentials.dependencies import get_authenticated_merchant
from app.merchant.models import Merchant
from app.rabbitmq.publisher import publish_payment_processing
from app.payment.schemas import (
    CreatePaymentRequest,
    CreatePaymentResponse,
)
from app.payment.service import PaymentService


router = APIRouter(
    prefix="/api/v1/payments",
    tags=["Payments"],
)


@router.post(
    "",
    response_model=CreatePaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    request: CreatePaymentRequest,
    merchant: Merchant = Depends(get_authenticated_merchant),
    db: Session = Depends(get_db),
) -> CreatePaymentResponse:

    payment_service = PaymentService()
    result = payment_service.create_payment(
        db=db,
        merchant_id=merchant.merchant_id,
        request=request,
    )
    if result.should_process:
        publish_payment_processing(
            payment_id=result.response.payment_id,
        )



    return result.response