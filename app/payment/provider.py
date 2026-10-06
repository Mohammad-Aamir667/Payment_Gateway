
from abc import ABC, abstractmethod
from uuid import UUID

from app.common.enums import Currency
from dataclasses import dataclass
from enum import Enum


class ProviderPaymentStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PROCESSING = "PROCESSING"


@dataclass
class ProviderPaymentResult:
    status: ProviderPaymentStatus
    provider_payment_id: str | None = None
    failure_reason: str | None = None

class PaymentServiceProvider(ABC):

    @abstractmethod
    def initiate_payment(
        self,
        payment_id: UUID,
        amount: int,
        currency: Currency,
        payment_method: str,
        payment_metadata: dict,
    )-> ProviderPaymentResult:
        pass

    @abstractmethod
    def get_payment_status(
        self,
        provider_payment_id: str,
    ) -> ProviderPaymentResult:
        pass

    @abstractmethod
    def find_payment_by_gateway_id(
        self,
        gateway_payment_id: UUID,
    ) -> ProviderPaymentResult | None: 
        pass
