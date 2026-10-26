
# app/outbox/publisher.py

import logging
import time
from uuid import UUID

from app.infrastructure.database import SessionLocal
from app.outbox.models import OutboxEventStatus
from app.outbox.repository import OutboxRepository
from app.rabbitmq.publisher import publish_message
from app.outbox.models import OutboxEvent

logger = logging.getLogger(__name__)

outbox_repository = OutboxRepository()

POLL_INTERVAL_SECONDS = 2
BATCH_SIZE = 100


def publish_pending_events() -> None:
    # Read only the IDs so each event can be processed
    # using its own database session.
    db = SessionLocal()
    try:
        events = outbox_repository.get_pending_events(
            db=db,
            limit=BATCH_SIZE,
        )
        event_ids = [event.outbox_event_id for event in events]

    finally:
        db.close()

    for event_id in event_ids:
        publish_outbox_event(event_id)


def publish_outbox_event(event_id: UUID) -> None:
    db = SessionLocal()
    try:
        event = outbox_repository.get_by_id(
            db=db,
            event_id=event_id,
        )

        if event is None:
            return

        if event.status != OutboxEventStatus.PENDING:
            return

        try:
            # Send the stored event to RabbitMQ.
            publish_message(
                routing_key=event.routing_key.value,
                payload=event.payload,
            )

        except Exception as exc:
            # The RabbitMQ publisher has already attempted
            # to close its connection in its finally block.
            db.rollback()

            event = outbox_repository.get_by_id(
                db=db,
                event_id=event_id,
            )

            if event is not None:
                outbox_repository.record_publish_failure(
                    db=db,
                    event=event,
                    error=str(exc),
                )
                db.commit()

            logger.exception(
                "Failed to publish outbox event %s",
                event_id,
            )
            return

        # Reached only when publish_message returned normally.
        outbox_repository.mark_as_published(
            db=db,
            event=event,
        )
        db.commit()

        logger.info(
            "Published outbox event %s",
            event_id,
        )
    except Exception:    
        logger.exception("Failed to publish outbox event %s", event_id)
    finally:
        db.close()



def run_outbox_publisher() -> None:
    logger.info("Outbox publisher started")

    while True:
        try:
            publish_pending_events()
            print("Published pending events")
        except Exception:
            logger.exception("Outbox polling cycle failed")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_outbox_publisher()
