from abc import ABC, abstractmethod
from uuid import UUID

from app.common.enums import Currency


class PaymentServiceProvider(ABC):

    @abstractmethod
    def initiate_payment(
        self,
        payment_id: UUID,
        amount: int,
        currency: Currency,
        payment_method: str,
        payment_metadata: dict,
    ):
        pass