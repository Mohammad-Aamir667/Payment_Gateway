# app/outbox/repository.py

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.outbox.models import (
    OutboxEvent,
    OutboxEventStatus,
)


class OutboxRepository:

    def create(
        self,
        db: Session,
        event: OutboxEvent,
    ) -> OutboxEvent:
        db.add(event)
        db.flush()
        return event

    def get_by_id(
        self,
        db: Session,
        event_id: UUID,
    ) -> OutboxEvent | None:
        return db.get(OutboxEvent, event_id)

    def get_pending_events(
        self,
        db: Session,
        limit: int = 100,
    ) -> list[OutboxEvent]:
        statement = (
            select(OutboxEvent)
            .where(
                OutboxEvent.status == OutboxEventStatus.PENDING
            )
            .order_by(OutboxEvent.created_at)
            .limit(limit)
        )

        return list(db.scalars(statement).all())

    def mark_as_published(
        self,
        db: Session,
        event: OutboxEvent,
    ) -> OutboxEvent:
        event.status = OutboxEventStatus.PUBLISHED
        event.published_at = datetime.now(timezone.utc)

        db.flush()
        return event

    def record_publish_failure(
        self,
        db: Session,
        event: OutboxEvent,
        error: str,
    ) -> OutboxEvent:
        event.attempt_count += 1
        event.last_error = error

        db.flush()
        return event