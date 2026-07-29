from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID
from app.merchant.models import Merchant


class MerchantRepository:
    """Handles all database operations related to merchants."""

    def get_by_email(
        self,
        db: Session,
        email: str,
    ) -> Merchant | None:

        statement = (
            select(Merchant)
            .where(Merchant.email == email)
        )

        result = db.execute(statement)

        return result.scalar_one_or_none()

    def create(
        self,
        db: Session,
        merchant: Merchant,
    ) -> Merchant:

       db.add(merchant)
       db.flush()
       db.refresh(merchant)
       return merchant

    def get_by_id(
        self,
        db: Session,
        merchant_id: UUID,
    ) -> Merchant | None:
        return (
            db.query(Merchant)
            .filter(
                Merchant.merchant_id == merchant_id,
            )
            .first()
        )
  