from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
)
from uuid import UUID

from enum import Enum

from datetime import datetime

class WebhookEventType(str, Enum):
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"


class WebhookCreateRequest(BaseModel):
    callback_url: HttpUrl = Field(
        description="Merchant webhook callback URL",
    )

    event_types: list[WebhookEventType] = Field(
        min_length=1,
        description="Events subscribed by the webhook",
    )

    password: str = Field(
        min_length=8,
        max_length=128,
        description="Merchant account password",
    )
    @field_validator("callback_url")
    @classmethod
    def validate_https(cls, value: HttpUrl):
        if value.scheme != "https":
            raise ValueError("Callback URL must use HTTPS.")
        return value

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class WebhookResponse(BaseModel):
    webhook_id: UUID

    callback_url: str

    event_types: list[WebhookEventType]

    is_active: bool

    webhook_secret: str

    created_at: datetime    


class WebhookUpdateRequest(BaseModel):
    callback_url: HttpUrl | None = None

    event_types: list[WebhookEventType] | None = None


    
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Merchant account password",
    )
    @field_validator("callback_url")
    @classmethod
    def validate_https(cls, value: HttpUrl):
        if value.scheme != "https":
            raise ValueError("Callback URL must use HTTPS.")
        return value

    


class WebhookUpdateResponse(BaseModel):
    webhook_id: UUID
    callback_url: str
    event_types: list[WebhookEventType]
    is_active: bool
    updated_at: datetime    


class WebhookDetailsResponse(BaseModel):
    webhook_id: UUID
    callback_url: str
    event_types: list[WebhookEventType]
    is_active: bool
    created_at: datetime
    updated_at: datetime    