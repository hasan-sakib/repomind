import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.repository_membership import RepositoryMembership
from app.schemas.user import UserPublic


class RepositoryMemberPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserPublic
    created_at: datetime

    @classmethod
    def from_membership(cls, membership: RepositoryMembership) -> "RepositoryMemberPublic":
        return cls(user=UserPublic.from_user(membership.user), created_at=membership.created_at)


class GrantRepositoryAccessRequest(BaseModel):
    user_id: uuid.UUID
