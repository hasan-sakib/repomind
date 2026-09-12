import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.role import Role
from app.schemas.user import UserPublic


class OrganizationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime

    @classmethod
    def from_organization(cls, organization: Organization) -> "OrganizationPublic":
        return cls(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            created_at=organization.created_at,
        )


class OrganizationMembershipPublic(BaseModel):
    organization: OrganizationPublic
    role: Role

    @classmethod
    def from_member(cls, member: OrganizationMember) -> "OrganizationMembershipPublic":
        return cls(
            organization=OrganizationPublic.from_organization(member.organization),
            role=member.role,
        )


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class MemberPublic(BaseModel):
    user: UserPublic
    role: Role
    created_at: datetime

    @classmethod
    def from_member(cls, member: OrganizationMember) -> "MemberPublic":
        return cls(
            user=UserPublic.from_user(member.user), role=member.role, created_at=member.created_at
        )


class AddMemberRequest(BaseModel):
    email: EmailStr
    role: Role = Role.DEVELOPER


class UpdateMemberRoleRequest(BaseModel):
    role: Role
