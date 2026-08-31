import time
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.enums import PaymentStatus
from app.payment.providers.factory import PaymentProviderFactory
from app.security.hashing import generate_request_hash

from app.payment.models import Payment
from app.payment.repository import PaymentRepository

from app.payment_history.models import PaymentHistory
from app.payment_history.repository import PaymentHistoryRepository

from app.idempotency.models import IdempotencyKey
from app.idempotency.repository import IdempotencyKeyRepository

from app.payment_methods.repository import PaymentMethodRepository
from app.merchant_payment_methods.repository import (
    MerchantPaymentMethodRepository,
)

from app.payment.schemas import (
    CreatePaymentRequest,
    CreatePaymentResponse,
)
class PaymentService:
    def __init__(self):
        self.payment_method_repository = PaymentMethodRepository()
   
    def create_payment(self,
        db: Session,
        merchant_id: UUID,
        request: CreatePaymentRequest,
    ) -> CreatePaymentResponse:

        # ---------------------------------------------------------
        # 1. Generate request hash
        # ---------------------------------------------------------

        request_for_hash = {
            "merchant_payment_method_id": str(
                request.merchant_payment_method_id
            ),
            "amount": request.amount,
            "currency": request.currency.value,
            "payment_metadata": request.payment_metadata,
        }

        request_hash = generate_request_hash(request_for_hash)

        # ---------------------------------------------------------
        # 2. Check existing idempotency record
        # ---------------------------------------------------------

        existing_record = IdempotencyKeyRepository.get_by_key(
            db=db,
            merchant_id=merchant_id,
            idempotency_key=request.idempotency_key,
        )


        if existing_record:

            # Same key, different request
            if existing_record.request_hash != request_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Idempotency key has already been used "
                        "for a different request."
                    ),
                )

            # Same key, same request
            return CreatePaymentResponse(
                **existing_record.response_snapshot
            )

        # ---------------------------------------------------------
        # 3. Validate Merchant Payment Method
        # ---------------------------------------------------------

        merchant_payment_method = (
            MerchantPaymentMethodRepository.get_by_id_for_merchant(
                db=db,
                merchant_payment_method_id=(
                    request.merchant_payment_method_id
                ),
                merchant_id=merchant_id,
            )
        )

        if merchant_payment_method is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant payment method not found.",
            )

        if not merchant_payment_method.is_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Merchant payment method is disabled.",
            )

        # ---------------------------------------------------------
        # 4. Retrieve Gateway Payment Method
        # ---------------------------------------------------------

        payment_method = self.payment_method_repository.get_by_id(
            db=db,
            payment_method_id=merchant_payment_method.payment_method_id,
        )

        if payment_method is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment method not found.",
            )

        if not payment_method.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Payment method is inactive.",
            )

        # ---------------------------------------------------------
        # 5. Create Payment
        # ---------------------------------------------------------

        payment = Payment(
            merchant_id=merchant_id,
            merchant_payment_method_id=(
                request.merchant_payment_method_id
            ),
            amount=request.amount,
            currency=request.currency,
            status=PaymentStatus.PROCESSING,
            payment_metadata=request.payment_metadata,
        )

        PaymentRepository.create(
            db=db,
            payment=payment,
        )

        # ---------------------------------------------------------
        # 6. Create Initial Payment History
        # ---------------------------------------------------------

        payment_history = PaymentHistory(
            payment_id=payment.payment_id,
            old_state=None,
            new_state=PaymentStatus.PROCESSING,
        )

        PaymentHistoryRepository.create(
            db=db,
            history=payment_history,
        )

        # ---------------------------------------------------------
        # 7. Build response
        # ---------------------------------------------------------

        response = CreatePaymentResponse(
            payment_id=payment.payment_id,
            status=payment.status,
            created_at=payment.created_at,
        )

        # ---------------------------------------------------------
        # 8. Create Idempotency Record
        # ---------------------------------------------------------

        idempotency_record = IdempotencyKey(
            merchant_id=merchant_id,
            payment_id=payment.payment_id,
            idempotency_key=request.idempotency_key,
            request_hash=request_hash,
            response_snapshot=response.model_dump(mode="json"),
        )
        # Handle potential race condition where two requests with the same idempotency key are processed concurrently.
        try:
            IdempotencyKeyRepository.create(
                db=db,
                idempotency_record=idempotency_record,
            )

        except IntegrityError as exc:

            constraint_name = exc.orig.diag.constraint_name
            print(f"IntegrityError: {exc.orig}, Constraint: {constraint_name}")
            if constraint_name != "uq_merchant_idempotency_key":
                raise

            db.rollback()

            existing_record = IdempotencyKeyRepository.get_by_key(
                db=db,
                merchant_id=merchant_id, 
                idempotency_key=request.idempotency_key,
            )

            if existing_record is None:
                # This should be treated as an unexpected condition.
                raise

            if existing_record.request_hash != request_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Idempotency key has already been used "
                        "for a different request."
                    ),
                )

            return CreatePaymentResponse(
                **existing_record.response_snapshot
            )
        # ---------------------------------------------------------
        # 9. Commit entire payment transaction
        # ---------------------------------------------------------

        
        db.commit()

        
        return response

    def process_payment(self,
        db: Session,
        payment_id: UUID,
    ) -> Payment:

        # 1. Retrieve payment
        payment = PaymentRepository.get_by_id(
            db=db,
            payment_id=payment_id,
        )

        if payment is None:
            raise ValueError("Payment not found.")

        # 2. Payment must still be processable
        if payment.status != PaymentStatus.PROCESSING:
            return payment

        # 3. Retrieve merchant payment method
        merchant_payment_method = (
            MerchantPaymentMethodRepository.get_by_id_for_merchant(
                db=db,
                merchant_payment_method_id=(
                    payment.merchant_payment_method_id
                ),
                merchant_id=payment.merchant_id,
            )
        )

        if merchant_payment_method is None:
            raise ValueError("Merchant payment method not found.")

        # 4. Retrieve gateway payment method
        payment_method = self.payment_method_repository.get_by_id(
            db=db,
            payment_method_id=merchant_payment_method.payment_method_id,
        )

        if payment_method is None:
            raise ValueError("Payment method not found.")

        # 5. Select provider
        provider = PaymentProviderFactory.get_provider(
            payment_method.code
        )

        # 6. Call external PSP
        provider_result = provider.initiate_payment(
            payment_id=payment.payment_id,
            amount=payment.amount,
            currency=payment.currency,
            payment_method=payment_method.code,
            payment_metadata=payment.payment_metadata,
        )

        provider_status = provider_result["status"]

        # 7. Timeout / uncertain result
        if provider_status == "PROCESSING":
            return payment

        # 8. Map provider result to gateway status
        if provider_status == "SUCCESS":
            new_status = PaymentStatus.SUCCESS

        elif provider_status == "FAILED":
            new_status = PaymentStatus.FAILED

        else:
            raise ValueError(
                f"Unknown provider status: {provider_status}"
            )

        # 9. Atomic gateway status transition
        try:
            PaymentRepository.update_status(
                db=db,
                payment=payment,
                status=new_status,
            )

            history = PaymentHistory(
                payment_id=payment.payment_id,
                old_state=PaymentStatus.PROCESSING,
                new_state=new_status,
            )

            PaymentHistoryRepository.create(
                db=db,
                history=history,
            )

            db.commit()

        except Exception:
            db.rollback()
            raise

        return payment

      