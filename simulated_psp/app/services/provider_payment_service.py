from decimal import Decimal
import asyncio
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.provider_payment import PaymentStatus, ProviderPayment
from app.repositories.provider_payment_repository import (
    ProviderPaymentRepository,
)
from app.exceptions.payment import PSPInternalError, PSPTimeoutError, ResponseLostError
from app.schemas.scenarios import PaymentScenario


class ProviderPaymentService:

    def __init__(self, db: Session):
        self.db = db
        self.repository = ProviderPaymentRepository(db)

    async def create_payment(
    self,
    gateway_payment_id: str,
    amount: Decimal,
    currency: str,
    scenario: PaymentScenario,
) -> dict:

        existing_payment = (
            self.repository.get_by_gateway_payment_id(
                gateway_payment_id
            )
        )

        if existing_payment:
            return self._to_response(existing_payment)

        if scenario == PaymentScenario.TIMEOUT_BEFORE_CREATE:
            await asyncio.sleep(10)
            raise PSPTimeoutError(
                "PSP timed out before creating payment."
            )
        

        payment = ProviderPayment(
            gateway_payment_id=gateway_payment_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.PROCESSING,
        )

        self.repository.create(payment)

        # Decide the PSP outcome.
        if scenario == PaymentScenario.SUCCESS:
            payment.status = PaymentStatus.SUCCESS

        elif scenario == PaymentScenario.FAILED:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = "Payment declined by PSP."

        elif scenario == PaymentScenario.PROCESSING:
            payment.status = PaymentStatus.PROCESSING

        self.db.commit()
        self.db.refresh(payment)

        if scenario == PaymentScenario.TIMEOUT_AFTER_CREATE:
           await asyncio.sleep(10)

           raise PSPTimeoutError(
                "PSP timed out after creating payment."
            )

     
        if scenario == PaymentScenario.INTERNAL_ERROR:
            raise PSPInternalError(
                "Simulated internal error in the PSP."
            )

        return self._to_response(payment)


    
    async def get_payment(
        self,
        provider_payment_id: str,
    ) -> dict:

        payment = self.repository.get_by_provider_payment_id(
            provider_payment_id
        )

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider payment not found."
            )

        return self._to_response(payment)

    async def get_payment_by_gateway_id(
        self,
        gateway_payment_id: str,
    ) -> dict:

        payment = self.repository.get_by_gateway_payment_id(
            gateway_payment_id
        )

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider payment not found."
            )

        return self._to_response(payment)
            
    @staticmethod
    def _to_response(payment: ProviderPayment) -> dict:
        return {
            "provider_payment_id": payment.provider_payment_id,
            "gateway_payment_id": payment.gateway_payment_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "failure_reason": payment.failure_reason,
        }