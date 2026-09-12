import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.api_key import ApiKey
from app.models.role import Role
from app.schemas.user import UserPublic


class ApiKeyPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_prefix: str
    role: Role
    created_by: UserPublic | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime

    @classmethod
    def from_api_key(cls, api_key: ApiKey) -> "ApiKeyPublic":
        return cls(
            id=api_key.id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            role=api_key.role,
            created_by=UserPublic.from_user(api_key.created_by) if api_key.created_by else None,
            last_used_at=api_key.last_used_at,
            revoked_at=api_key.revoked_at,
            created_at=api_key.created_at,
        )


class ApiKeyCreatedPublic(ApiKeyPublic):
    """Only ever returned once, from the create endpoint — the plaintext
    secret is not recoverable afterward."""

    secret: str

    @classmethod
    def from_api_key_and_secret(cls, api_key: ApiKey, secret: str) -> "ApiKeyCreatedPublic":
        return cls(**ApiKeyPublic.from_api_key(api_key).model_dump(), secret=secret)


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    role: Role = Role.VIEWER
