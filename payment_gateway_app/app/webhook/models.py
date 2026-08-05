from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    func,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import (
    UUID as PGUUID,
    ARRAY,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base
from sqlalchemy import UniqueConstraint


class WebhookEventType(str, Enum):
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"


class Webhook(Base):
    __tablename__ = "webhooks"

    __table_args__ = (
        UniqueConstraint(
            "merchant_id",
            name="uq_webhook_merchant",
        ),
    )
    webhook_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    merchant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("merchant.merchant_id"),
        nullable=False,
    )

    callback_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    event_types: Mapped[list[WebhookEventType]] = mapped_column(
        ARRAY(
            SQLEnum(
                WebhookEventType,
                name="webhook_event_type_enum",
            )
        ),
        nullable=False,
    )

    webhook_secret: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )