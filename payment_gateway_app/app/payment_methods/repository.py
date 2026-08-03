from sqlalchemy.orm import Session

from app.payment_methods.models import PaymentMethod


class PaymentMethodRepository:

    def get_by_code(
        self,
        db: Session,
        code: str,
    ) -> PaymentMethod | None:

        return (
            db.query(PaymentMethod)
            .filter(
                PaymentMethod.code == code,
            )
            .first()
        )