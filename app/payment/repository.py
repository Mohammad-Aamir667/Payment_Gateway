from uuid import UUID

from sqlalchemy.orm import Session

from app.payment.models import Payment
from app.common.enums import PaymentStatus


class PaymentRepository:

    @staticmethod
    def create(
        db: Session,
        payment: Payment,
    ) -> Payment:
        db.add(payment)
        db.flush()

        return payment

    @staticmethod
    def update_status(
        db: Session,
        payment: Payment,
        status: PaymentStatus,
    ) -> Payment:
        payment.status = status
        db.flush()

        return payment