from pydantic import BaseModel, Field,ConfigDict
from datetime import datetime
from uuid import UUID
from enum import Enum

class APIKeyCreateRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )
    key_name: str = Field(
    min_length=3,
    max_length=50,
    description="Friendly name for the API key.",
    examples=["Production"],
)
    password: str = Field(
    min_length=8,
    max_length=128,
    description="Merchant account password.",
    examples=["MySecurePassword123"],
)
class APIKeyResponse(BaseModel):
    key_name: str = Field(
        min_length=3,
        max_length=50,
        description="Merchant's API key name"
    )
    api_key: str = Field(
    description="Plain API key. Displayed only once during creation."
)
    created_at: datetime = Field(
    description="Timestamp when the API key was created."
)
class KeyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    

class APIKeyMetadataResponse(BaseModel):
    api_key_id: UUID
    key_name: str
    key_status: KeyStatus
    created_at: datetime
    revoked_at: datetime | None


class APIKeyListResponse(BaseModel):
    api_keys: list[APIKeyMetadataResponse]    
