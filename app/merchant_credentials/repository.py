from sqlalchemy.orm import Session
from uuid import UUID
from app.merchant_credentials.models import APIKey


class APIKeyRepository:

    def get_by_merchant_and_key_name(
        self,
        db: Session,
        merchant_id: UUID,
        key_name: str,
    ) -> APIKey | None:

        return (
            db.query(APIKey)
            .filter(
                APIKey.merchant_id == merchant_id,
                APIKey.key_name == key_name,
            )
            .first()
        )

    def create(
        self,
        db: Session,
        api_key: APIKey,
    ) -> APIKey:

        db.add(api_key)

        return api_key

    def get_by_merchant_id(
        self,
        db: Session,
        merchant_id: UUID,
    ) -> list[APIKey]:

        return (
            db.query(APIKey)
            .filter(
                APIKey.merchant_id == merchant_id,
            )
            .order_by(APIKey.created_at.desc())
            .all()
        )
    
    def get_by_id(
    self,
    db: Session,
    api_key_id: UUID,
) -> APIKey | None:

        return (
        db.query(APIKey)
        .filter(
            APIKey.api_key_id == api_key_id,
        )
        .first()
    )


    def get_by_hash(self,
        db: Session,
        api_key_hash: str,
    ) -> APIKey | None:
        return (
            db.query(APIKey)
            .filter(APIKey.api_key_hash == api_key_hash)
            .first()
        )