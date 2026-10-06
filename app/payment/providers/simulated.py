from decimal import Decimal
from uuid import UUID

import httpx

from app.payment.exceptions import (
    ProviderConnectionError,
    ProviderInternalError,
    ProviderResponseLostError,
    ProviderTimeoutError,
)
from app.payment.provider import (
    PaymentServiceProvider,
    ProviderPaymentResult,
    ProviderPaymentStatus,
)
from app.core.settings import settings



class SimulatedPaymentServiceProvider(PaymentServiceProvider):

    PSP_BASE_URL = settings.PSP_BASE_URL

    # Manual testing switches.
    # Keep these False normally.
    SIMULATE_RESPONSE_LOST = False

    def initiate_payment(
        self,
        payment_id: UUID,
        amount: Decimal,
        currency: str,
        payment_method: str,
        payment_metadata: dict | None,
    ) -> ProviderPaymentResult:

        payload = {
            "gateway_payment_id": str(payment_id),
            "amount": amount,
            "currency": currency,
        }

        try:
            response = httpx.post(
                f"{self.PSP_BASE_URL}/payments",
                json=payload,
                timeout=5.0,
            )

        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                "Payment provider request timed out."
            ) from exc

        except httpx.RequestError as exc:
            raise ProviderConnectionError(
                "Could not communicate with payment provider."
            ) from exc

        if self.SIMULATE_RESPONSE_LOST:
            raise ProviderResponseLostError(
                "Provider response was intentionally discarded."
            )

        try:
            response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            if response.status_code >= 500:
                raise ProviderInternalError(
                    f"Provider returned HTTP {response.status_code}."
                ) from exc

            raise ProviderConnectionError(
                f"Unexpected provider HTTP status: {response.status_code}."
            ) from exc
        print(f"Provider response: {response.json()}")
        return self._to_provider_result(response.json())

    def get_payment_status(
        self,
        provider_payment_id: str,
    ) -> ProviderPaymentResult:

        try:
            response = httpx.get(
                f"{self.PSP_BASE_URL}/payments/{provider_payment_id}",
                timeout=5.0,
            )

        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                "Payment provider status request timed out."
            ) from exc

        except httpx.RequestError as exc:
            raise ProviderConnectionError(
                "Could not communicate with payment provider."
            ) from exc

        if self.SIMULATE_RESPONSE_LOST:
            raise ProviderResponseLostError(
                "Provider status response was intentionally discarded."
            )

        try:
            response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            if response.status_code >= 500:
                raise ProviderInternalError(
                    f"Provider returned HTTP {response.status_code}."
                ) from exc

            raise ProviderConnectionError(
                f"Unexpected provider HTTP status: {response.status_code}."
            ) from exc

        return self._to_provider_result(response.json())

    def find_payment_by_gateway_id(
        self,
        gateway_payment_id: UUID,
    ) -> ProviderPaymentResult | None:

        try:
            response = httpx.get(
                f"{self.PSP_BASE_URL}/payments/by-gateway/{gateway_payment_id}",
                timeout=5.0,
            )

        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                "Payment provider lookup request timed out."
            ) from exc

        except httpx.RequestError as exc:
            raise ProviderConnectionError(
                "Could not communicate with payment provider."
            ) from exc

        if self.SIMULATE_RESPONSE_LOST:
            raise ProviderResponseLostError(
                "Provider lookup response was intentionally discarded."
            )

        # A lookup returning 404 simply means:
        # "the provider does not know about this gateway payment."
        if response.status_code == 404:
            return None

        try:
            response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            if response.status_code >= 500:
                raise ProviderInternalError(
                    f"Provider returned HTTP {response.status_code}."
                ) from exc

            raise ProviderConnectionError(
                f"Unexpected provider HTTP status: {response.status_code}."
            ) from exc

        # IMPORTANT:
        # This already contains the provider status.
        # We return it directly.
        return self._to_provider_result(response.json())

    @staticmethod
    def _to_provider_result(data: dict) -> ProviderPaymentResult:
        return ProviderPaymentResult(
            status=ProviderPaymentStatus(data["status"]),
            provider_payment_id=data.get("provider_payment_id"),
            failure_reason=data.get("failure_reason"),
        )