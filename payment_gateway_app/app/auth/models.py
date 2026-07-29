from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy import Enum as PGEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class DeviceIdentifier(str, Enum):
    LAPTOP = "LAPTOP"
    PHONE = "PHONE"
    TABLET = "TABLET"
    PC = "PC"


class RefreshToken(Base):
    __tablename__ = "refresh_token"

    refresh_token_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    merchant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("merchant.merchant_id"),
        nullable=False,
    )

    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    device_identifier: Mapped[DeviceIdentifier] = mapped_column(
        PGEnum(DeviceIdentifier, name="device_identifier"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<RefreshToken("
            f"id={self.refresh_token_id}, "
            f"merchant={self.merchant_id}, "
            f"device={self.device_identifier})>"
        )