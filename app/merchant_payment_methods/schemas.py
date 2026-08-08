from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime


class MerchantPaymentMethodCreateRequest(BaseModel):
    payment_method: str = Field(
        min_length=2,
        max_length=50,
        description="Gateway supported payment method code",
    )

    password: str = Field(
        min_length=8,
        max_length=128,
        description="Merchant account password",
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class MerchantPaymentMethodResponse(BaseModel):
    merchant_payment_method_id: UUID

    merchant_id: UUID

    payment_method_id: UUID

    payment_method: str

    display_name: str

    is_enabled: bool

    created_at: datetime

    updated_at: datetime    

class MerchantPaymentMethodItemResponse(BaseModel):
    merchant_payment_method_id: UUID
    payment_method_id: UUID
    payment_method: str
    display_name: str
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class MerchantPaymentMethodListResponse(BaseModel):
    payment_methods: list[MerchantPaymentMethodItemResponse]    