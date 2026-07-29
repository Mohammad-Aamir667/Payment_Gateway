from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.infrastructure.database import Base


class MerchantStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"


class Merchant(Base):
    __tablename__ = "merchant"

    def __repr__(self) -> str:
        return (
            f"<Merchant("
            f"merchant_id={self.merchant_id}, "
            f"business_name='{self.business_name}', "
            f"email='{self.email}')>"
        )
    
    merchant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    business_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    merchant_status: Mapped[MerchantStatus] = mapped_column(
        SQLEnum(MerchantStatus, name="merchant_status_enum"),
        nullable=False,
        default=MerchantStatus.ACTIVE,
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