from uuid import UUID

from sqlalchemy.orm import Session

from app.webhook.models import Webhook


class WebhookRepository:

    def get_by_merchant(
        self,
        db: Session,
        merchant_id: UUID,
    ) -> Webhook | None:
        return (
            db.query(Webhook)
            .filter(
                Webhook.merchant_id == merchant_id,
            )
            .first()
        )

    def get_by_id(
        self,
        db: Session,
        webhook_id: UUID,
    ) -> Webhook | None:
        return (
            db.query(Webhook)
            .filter(
                Webhook.webhook_id == webhook_id,
            )
            .first()
        )

    def create(
        self,
        db: Session,
        webhook: Webhook,
    ) -> None:
        db.add(webhook)

    def update(
        self,
        db: Session,
        webhook: Webhook,
    ) -> None:
        db.add(webhook)

    def delete(
        self,
        db: Session,
        webhook: Webhook,
    ) -> None:
        db.delete(webhook)