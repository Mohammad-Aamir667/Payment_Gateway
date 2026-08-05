from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.merchant.models import Merchant
from app.merchant_payment_methods.model import MerchantPaymentMethod

from app.payment_methods.repository import PaymentMethodRepository
from app.merchant_payment_methods.repository import (
    MerchantPaymentMethodRepository,
)
from app.merchant_payment_methods.schemas import (
    MerchantPaymentMethodCreateRequest,
    MerchantPaymentMethodListResponse,
    MerchantPaymentMethodResponse,
    MerchantPaymentMethodItemResponse,
)

from app.security.passwords import verify_password


class MerchantPaymentMethodService:

    def __init__(self,payment_method_repository: PaymentMethodRepository,merchant_payment_method_repository: MerchantPaymentMethodRepository,
    ):
        self.payment_method_repository = payment_method_repository
        self.merchant_payment_method_repository = (
            merchant_payment_method_repository
        )

    def create_merchant_payment_method(
        self,
        merchant: Merchant,
        request: MerchantPaymentMethodCreateRequest,
        db: Session,
    ) -> MerchantPaymentMethodResponse:

        # Verify merchant password
        if not verify_password(
            request.password,
            merchant.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password.",
            )

        # Retrieve gateway payment method
        payment_method = (
            self.payment_method_repository.get_by_code(
                db=db,
                code=request.payment_method,
            )
        )

        if payment_method is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment method does not exist.",
            )

        # Verify gateway payment method is active
        if not payment_method.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment method is currently unavailable.",
            )

        # Check whether merchant already enabled it
        existing_payment_method = (
            self.merchant_payment_method_repository
            .get_by_merchant_and_payment_method(
                db=db,
                merchant_id=merchant.merchant_id,
                payment_method_id=payment_method.payment_method_id,
            )
        )

        if existing_payment_method is not None:

            if existing_payment_method.is_enabled:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Merchant has already enabled this payment method.",
                )

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment method already exists but is currently disabled. Please enable it.",
            )

        # Create merchant payment method
        merchant_payment_method = MerchantPaymentMethod(
            merchant_id=merchant.merchant_id,
            payment_method_id=payment_method.payment_method_id,
        )

        self.merchant_payment_method_repository.create(
            db=db,
            merchant_payment_method=merchant_payment_method,
        )

        db.commit()
        db.refresh(merchant_payment_method)

        return MerchantPaymentMethodResponse(
            merchant_payment_method_id=merchant_payment_method.merchant_payment_method_id,
            merchant_id=merchant_payment_method.merchant_id,
            payment_method_id=merchant_payment_method.payment_method_id,
            payment_method=payment_method.code,
            display_name=payment_method.display_name,
            is_enabled=merchant_payment_method.is_enabled,
            created_at=merchant_payment_method.created_at,
            updated_at=merchant_payment_method.updated_at,
        )

    

    def list_merchant_payment_methods(
        self,
        merchant: Merchant,
        db: Session,
    ) -> MerchantPaymentMethodListResponse:

        merchant_payment_methods = (
            self.merchant_payment_method_repository
            .get_by_merchant(
                db=db,
                merchant_id=merchant.merchant_id,
            )
        )

        payment_methods = []

        for merchant_payment_method in merchant_payment_methods:

            payment_method = (
                self.payment_method_repository.get_by_id(
                    db=db,
                    payment_method_id=merchant_payment_method.payment_method_id,
                )
            )

            payment_methods.append(
                MerchantPaymentMethodItemResponse(
                    merchant_payment_method_id=merchant_payment_method.merchant_payment_method_id,
                    payment_method_id=merchant_payment_method.payment_method_id,
                    payment_method=payment_method.code,
                    display_name=payment_method.display_name,
                    is_enabled=merchant_payment_method.is_enabled,
                    created_at=merchant_payment_method.created_at,
                    updated_at=merchant_payment_method.updated_at,
                )
            )

        return MerchantPaymentMethodListResponse(
            payment_methods=payment_methods,
        )