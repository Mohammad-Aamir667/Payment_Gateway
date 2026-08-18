from sqlalchemy.orm import Session
from uuid import UUID
from app.merchant_payment_methods.model import MerchantPaymentMethod


class MerchantPaymentMethodRepository:

    def get_by_merchant_and_payment_method(
        self,
        db: Session,
        merchant_id: UUID,
        payment_method_id: UUID,
    ) -> MerchantPaymentMethod | None:

        return (
            db.query(MerchantPaymentMethod)
            .filter(
                MerchantPaymentMethod.merchant_id == merchant_id,
                MerchantPaymentMethod.payment_method_id == payment_method_id,
            )
            .first()
        )

    def create(
        self,
        db: Session,
        merchant_payment_method: MerchantPaymentMethod,
    ) -> None:

        db.add(merchant_payment_method)

    def get_by_id(
        self,
        db: Session,
        merchant_payment_method_id: UUID,
    ) -> MerchantPaymentMethod | None:

        return (
            db.query(MerchantPaymentMethod)
            .filter(
                MerchantPaymentMethod.merchant_payment_method_id
                == merchant_payment_method_id,
            )
            .first()
        )
    
    def get_by_merchant(
        self,
        db: Session,
        merchant_id: UUID,
    ) -> list[MerchantPaymentMethod]:

        return (
            db.query(MerchantPaymentMethod)
            .filter(
                MerchantPaymentMethod.merchant_id == merchant_id,
            )
            .all()
        )

    @staticmethod
    def get_by_id_for_merchant(
        db: Session,
        merchant_payment_method_id: UUID,
        merchant_id: UUID,
    ) -> MerchantPaymentMethod | None:
        return (
            db.query(MerchantPaymentMethod)
            .filter(
                MerchantPaymentMethod.merchant_payment_method_id
                == merchant_payment_method_id,
                MerchantPaymentMethod.merchant_id
                == merchant_id,
            )
            .first()
        )