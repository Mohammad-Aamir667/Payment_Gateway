import uuid
from sqlalchemy import BigInteger, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.infrastructure.database import Base

from enum import Enum
from app.common.enums import PaymentStatus
from datetime import datetime
from app.common.enums import Currency

class Payment(Base):
    __tablename__ = "payments"

    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchant.merchant_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    merchant_payment_method_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "merchant_payment_methods.merchant_payment_method_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    currency: Mapped[Currency] = mapped_column(
        PGEnum(Currency, name="currency", create_type=False),
        nullable=False,
    )

    status: Mapped[PaymentStatus] = mapped_column(
        PGEnum(PaymentStatus, name="paymentstatus", create_type=False),
        nullable=False,
    )

    payment_metadata: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
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