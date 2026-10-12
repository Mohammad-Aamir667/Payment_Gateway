
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SQLAlchemyEnum,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class OutboxEventType(str, Enum):
    PAYMENT_PROCESS = "PAYMENT_PROCESS"


class AggregateType(str, Enum):
    PAYMENT = "PAYMENT"
    MERCHANT = "MERCHANT"
class OutboxRoutingKey(str, Enum):
    PAYMENT_PROCESS = "payment.process"
    WEBHOOK_DELIVER = "webhook.deliver"

class OutboxEventStatus(str, Enum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    outbox_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    event_type: Mapped[OutboxEventType] = mapped_column(
        SQLAlchemyEnum(
            OutboxEventType,
            name="outbox_event_type",
            values_callable=lambda enum_cls: [
                member.value for member in enum_cls
            ],
        ),
        nullable=False,
    )
    routing_key: Mapped[OutboxRoutingKey] = mapped_column(
        SQLAlchemyEnum(
            OutboxRoutingKey,
            name="outbox_routing_key",
            values_callable=lambda enum_cls: [
                member.value for member in enum_cls
            ],
        ),
        nullable=False,
    )

    aggregate_type: Mapped[AggregateType] = mapped_column(
        SQLAlchemyEnum(
            AggregateType,
            name="aggregate_type",
            values_callable=lambda enum_cls: [
                member.value for member in enum_cls
            ],
        ),
        nullable=False,
    )

    aggregate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    status: Mapped[OutboxEventStatus] = mapped_column(
        SQLAlchemyEnum(
            OutboxEventStatus,
            name="outbox_event_status",
            values_callable=lambda enum_cls: [
                member.value for member in enum_cls
            ],
        ),
        nullable=False,
        default=OutboxEventStatus.PENDING,
        server_default=text("'PENDING'"),
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    last_error: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_outbox_events_status_created_at",
            "status",
            "created_at",
        ),
    )