from pydantic import BaseModel, ConfigDict, Field


class PasswordRequest(BaseModel):
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Merchant account password",
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )