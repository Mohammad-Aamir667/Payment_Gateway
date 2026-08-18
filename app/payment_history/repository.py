from sqlalchemy.orm import Session

from app.payment_history.models import PaymentHistory


class PaymentHistoryRepository:

    @staticmethod
    def create(
        db: Session,
        history: PaymentHistory,
    ) -> PaymentHistory:
        db.add(history)
        db.flush()

        return history