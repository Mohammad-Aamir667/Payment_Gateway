from uuid import UUID

from sqlalchemy.orm import Session

from app.outbox.models import (
    OutboxEvent,
    OutboxEventType,
    OutboxRoutingKey,
    AggregateType,
    OutboxEventStatus,
)
from app.outbox.repository import OutboxRepository


class OutboxService:
    def __init__(self):
        self.outbox_repository = OutboxRepository()

    def create_payment_processing_event(
        self,
        db: Session,
        payment_id: UUID,
    ) -> OutboxEvent:
        event = OutboxEvent(
            event_type=OutboxEventType.PAYMENT_PROCESS,
            routing_key=OutboxRoutingKey.PAYMENT_PROCESS,
            aggregate_type=AggregateType.PAYMENT,
            aggregate_id=payment_id,
            payload={
                "payment_id": str(payment_id),
            },
            status=OutboxEventStatus.PENDING,
        )

        return self.outbox_repository.create(db, event)


