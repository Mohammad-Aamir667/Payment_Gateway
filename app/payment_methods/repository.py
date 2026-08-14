from uuid import UUID

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

    def get_by_id(
    self,
    db: Session,
    payment_method_id: UUID,
) -> PaymentMethod | None:

        return (
            db.query(PaymentMethod)
            .filter(
                PaymentMethod.payment_method_id == payment_method_id,
            )
            .first()
        )

  