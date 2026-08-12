from uuid import UUID

from sqlalchemy.orm import Session

from app.idempotency.models import IdempotencyKey


class IdempotencyKeyRepository:

    @staticmethod
    def get_by_key(
        db: Session,
        merchant_id: UUID,
        idempotency_key: str,
    ) -> IdempotencyKey | None:
        return (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.merchant_id == merchant_id,
                IdempotencyKey.idempotency_key == idempotency_key,
            )
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        idempotency_record: IdempotencyKey,
    ) -> IdempotencyKey:
        db.add(idempotency_record)
        db.flush()

        return idempotency_record