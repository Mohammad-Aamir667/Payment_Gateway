from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.provider_payment import ProviderPayment


class ProviderPaymentRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, payment: ProviderPayment) -> ProviderPayment:
        self.db.add(payment)
        self.db.flush()

        return payment

    def get_by_provider_payment_id(
        self,
        provider_payment_id: str,
    ) -> ProviderPayment | None:
        stmt = select(ProviderPayment).where(
            ProviderPayment.provider_payment_id == provider_payment_id
        )

        return self.db.scalar(stmt)

    def get_by_gateway_payment_id(
        self,
        gateway_payment_id: str,
    ) -> ProviderPayment | None:
        stmt = select(ProviderPayment).where(
            ProviderPayment.gateway_payment_id == gateway_payment_id
        )

        return self.db.scalar(stmt)

    def update(self, payment: ProviderPayment) -> ProviderPayment:
        self.db.flush()

        return payment