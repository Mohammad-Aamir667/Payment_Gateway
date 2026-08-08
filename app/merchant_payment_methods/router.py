from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.merchant.models import Merchant

from app.merchant.dependencies import get_current_merchant
from app.payment_methods.repository import PaymentMethodRepository
from app.merchant_payment_methods.repository import (
    MerchantPaymentMethodRepository,
)
from app.merchant_payment_methods.schemas import (
    MerchantPaymentMethodCreateRequest,
    MerchantPaymentMethodListResponse,
    MerchantPaymentMethodResponse,
)
from app.merchant_payment_methods.service import (
    MerchantPaymentMethodService,
)


router = APIRouter(prefix="/merchant-payment-methods",
    tags=["Merchant Payment Methods"],
)

merchant_payment_method_service = MerchantPaymentMethodService(
    payment_method_repository=PaymentMethodRepository(),
    merchant_payment_method_repository=MerchantPaymentMethodRepository(),
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=MerchantPaymentMethodResponse,
)
def create_merchant_payment_method(
    request: MerchantPaymentMethodCreateRequest,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return merchant_payment_method_service.create_merchant_payment_method(
        merchant=merchant,
        request=request,
        db=db,
    )


@router.get(
    "",
    response_model=MerchantPaymentMethodListResponse,
)
def list_merchant_payment_methods(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return merchant_payment_method_service.list_merchant_payment_methods(
        merchant=merchant,
        db=db,
    )