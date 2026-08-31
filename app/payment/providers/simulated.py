from uuid import UUID

from app.common.enums import Currency
from app.payment.provider import PaymentServiceProvider


class SimulatedPaymentServiceProvider(PaymentServiceProvider):

    def initiate_payment(
        self,
        payment_id: UUID,
        amount: int,
        currency: Currency,
        payment_method: str,
        payment_metadata: dict,
    ) -> dict:

        # Deterministic simulation rules.
        # These are intentionally simple and only exist
        # to simulate external PSP behavior.

        if amount == 1000:
            return {
                "status": "SUCCESS",
                "provider_payment_id": f"sim_{payment_id}",
            }

        if amount == 2000:
            return {
                "status": "FAILED",
                "provider_payment_id": f"sim_{payment_id}",
                "failure_reason": "SIMULATED_PAYMENT_FAILURE",
            }

        if amount == 3000:
            return {
                "status": "PROCESSING",
                "provider_payment_id": f"sim_{payment_id}",
            }

        if amount == 4000:
            raise TimeoutError("Simulated PSP timeout")

        return {
            "status": "SUCCESS",
            "provider_payment_id": f"sim_{payment_id}",
        }