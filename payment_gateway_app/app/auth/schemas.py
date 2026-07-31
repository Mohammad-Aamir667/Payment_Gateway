from pydantic import BaseModel, ConfigDict, EmailStr, Field
from uuid import UUID

from enum import Enum
from app.merchant.models import MerchantStatus


class DeviceType(str, Enum):
    LAPTOP = "LAPTOP"
    PHONE = "PHONE"
    TABLET = "TABLET"
    PC = "PC"

class MerchantSignupRequest(BaseModel):
    business_name: str = Field(
        min_length=3,
        max_length=100,
        description="Merchant's registered business name"
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
        description="Merchant account password"
    )
    device_identifier: DeviceType

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class MerchantResponse(BaseModel):
    merchant_id: UUID
    business_name: str
    email: str
    merchant_status: MerchantStatus

    model_config = ConfigDict(
        from_attributes=True,
    )
class AuthenticationResponse(BaseModel):
    merchant: MerchantResponse
   

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )

class MerchantLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Merchant account password"
    )
    device_identifier: DeviceType

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

class MessageResponse(BaseModel):
    message: str    

class DeviceIdentifier(BaseModel):
    device_identifier:DeviceType    