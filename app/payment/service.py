from dataclasses import dataclass
import time
from urllib import response
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.payment.models import Payment 
from app.common.enums import PaymentStatus
from app.payment.exceptions import MerchantPaymentMethodNotFoundError, PaymentMethodNotFoundError, PaymentNotFoundError, ProviderCommunicationError, UnknownProviderStatusError
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
from app.payment.provider import ProviderPaymentStatus

from app.payment.schemas import (
    CreatePaymentRequest,
    CreatePaymentResponse,
)
from dataclasses import dataclass

@dataclass
class CreatePaymentResult:
    response: CreatePaymentResponse
    should_process: bool

class PaymentService:
    def __init__(self):
        self.payment_method_repository = PaymentMethodRepository()
   
    def create_payment(self,
        db: Session,
        merchant_id: UUID,
        request: CreatePaymentRequest,
    ) -> CreatePaymentResult:

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
            return CreatePaymentResult(
                response=CreatePaymentResponse(
                    **existing_record.response_snapshot
                ),
                should_process=False,
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

            return CreatePaymentResult(
                response=CreatePaymentResponse(
                    **existing_record.response_snapshot
                ),
                should_process=False,
            )
        # ---------------------------------------------------------
        # 9. Commit entire payment transaction
        # ---------------------------------------------------------

        
        db.commit()
        # return response
        
        return CreatePaymentResult(
        response=response,
        should_process=True,
    )
        
       
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
            raise PaymentNotFoundError(
        f"Payment {payment_id} not found."
    )

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
            raise MerchantPaymentMethodNotFoundError(
        f"Merchant payment method not found for payment {payment_id}."
    )
        # 4. Retrieve gateway payment method
        payment_method = self.payment_method_repository.get_by_id(
            db=db,
            payment_method_id=merchant_payment_method.payment_method_id,
        )

        if payment_method is None:
            raise PaymentMethodNotFoundError(
        f"Payment method not found for payment {payment_id}."
    )
        # 5. Select provider
        provider = PaymentProviderFactory.get_provider(
            payment_method.code
        )

        # 6. Determine whether a provider-side payment already exists

        # 6. Determine the provider result
        try:
            if payment.provider_payment_id is not None:
                # Provider payment already known.
                # Retrieve its current status.
                provider_result = provider.get_payment_status(
                    provider_payment_id=payment.provider_payment_id,
                )

            else:
                # We don't know the provider payment ID.
                # First check whether PSP already created a payment.
                existing_provider_payment = (
                    provider.find_payment_by_gateway_id(
                        gateway_payment_id=payment.payment_id,
                    )
                )

                if existing_provider_payment is not None:
                    # PSP payment already exists, so retrieve its current status.
                    provider_result = existing_provider_payment
                else:
                   
                    provider_result = provider.initiate_payment(
                                    payment_id=payment.payment_id,
                                    amount=payment.amount,
                                    currency=payment.currency,
                                    payment_method=payment_method.code,
                                    payment_metadata=payment.payment_metadata,
                                )
                    
        except ProviderCommunicationError:
            db.rollback()
            raise
                            
                        # Persist the PSP's external payment reference whenever provided.
        if provider_result.provider_payment_id is not None and payment.provider_payment_id is None:
            payment.provider_payment_id = (
                                            provider_result.provider_payment_id
                         )
        #  we can safely commit the payment here as the status is still Processing and payment history already exists for this status. This ensures that the provider_payment_id is persisted in the database before we proceed to update the payment status based on the provider's response. the life cycle of payment history is already handled in the previous steps, so we don't need to create a new payment history entry for this update. The payment history will only be updated when the status changes from Processing to either Success or Failed, which will be handled in the next steps.
        if provider_result.status == ProviderPaymentStatus.PROCESSING and payment.provider_payment_id is not None:
                                        db.commit()
                                        return payment
                            
        if provider_result.status == ProviderPaymentStatus.SUCCESS:
            new_status = PaymentStatus.SUCCESS
                            
        elif provider_result.status == ProviderPaymentStatus.FAILED:
            new_status = PaymentStatus.FAILED
                            
        else:
            raise UnknownProviderStatusError(
        f"Unknown provider status: {provider_result.status}"
    )
                
                # No provider-side payment exists, so this is the
                # point where initiating a new payment is appropriate.
               
               # 6. Call external PSP
       
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
            db.refresh(payment)
        except Exception as e:
            print(f"Error updating payment status for {payment_id}: {e}")
            db.rollback()
            raise

        return payment

      