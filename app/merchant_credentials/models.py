from uuid import UUID, uuid4
from sqlalchemy import String, DateTime, func, Enum as SQLEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from enum import Enum
from datetime import datetime



class KeyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    

class APIKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (
        UniqueConstraint(
            "merchant_id",
            "key_name",
            name="uq_merchant_key_name",
        )),
    api_key_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True),
            primary_key=True,
            default=uuid4,
            )
    merchant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("merchant.merchant_id"),
        nullable=False,
    )
    
    api_key_hash:Mapped[str] = mapped_column(
        String(255),
         nullable=False,
         unique=True,
    )        
    
    key_name: Mapped[str] = mapped_column(
        String(255),
        nullable = False,
    )
    key_status: Mapped[KeyStatus] = mapped_column(
        SQLEnum(KeyStatus, name="key_status_enum"),
        nullable=False,
        default=KeyStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )    
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
)



