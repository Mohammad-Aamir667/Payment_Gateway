from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.merchant_credentials.dependencies import get_authenticated_merchant
from app.merchant.models import Merchant

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
    response = payment_service.create_payment(
        db=db,
        merchant_id=merchant.merchant_id,
        request=request,
    )
    payment = payment_service.process_payment(
        db=db,payment_id=response.payment_id
    )
    print(f"Payment processed: {payment.payment_id}, Status: {payment.status}")
    return response