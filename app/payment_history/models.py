import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.infrastructure.database import Base
from app.common.enums import PaymentStatus

class PaymentHistory(Base):
    __tablename__ = "payment_history"

    history_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.payment_id"),
        nullable=False,
        index=True,
    )

    

    old_state: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus),
        nullable=False,
    )

    new_state: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus),
        nullable=False,
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )