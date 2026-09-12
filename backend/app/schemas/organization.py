import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.billing.plans import PlanLimits
from app.billing.usage import UsageSummary
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.plan import Plan
from app.models.role import Role
from app.schemas.user import UserPublic


class OrganizationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan: Plan
    created_at: datetime

    @classmethod
    def from_organization(cls, organization: Organization) -> "OrganizationPublic":
        return cls(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            plan=organization.plan,
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


class UpdateOrganizationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class SetPlanRequest(BaseModel):
    plan: Plan


class PlanLimitsPublic(BaseModel):
    max_repositories: int | None
    max_members: int | None

    @classmethod
    def from_limits(cls, limits: PlanLimits) -> "PlanLimitsPublic":
        return cls(max_repositories=limits.max_repositories, max_members=limits.max_members)


class UsageSummaryPublic(BaseModel):
    plan: Plan
    limits: PlanLimitsPublic
    repositories_used: int
    members_used: int
    ai_tokens_used: int
    indexing_runs: int
    pr_analyses_run: int
    onboarding_guides_generated: int
    analytics_snapshots_generated: int

    @classmethod
    def from_usage(
        cls, *, plan: Plan, limits: PlanLimits, usage: UsageSummary
    ) -> "UsageSummaryPublic":
        return cls(
            plan=plan,
            limits=PlanLimitsPublic.from_limits(limits),
            repositories_used=usage.repositories_used,
            members_used=usage.members_used,
            ai_tokens_used=usage.ai_tokens_used,
            indexing_runs=usage.indexing_runs,
            pr_analyses_run=usage.pr_analyses_run,
            onboarding_guides_generated=usage.onboarding_guides_generated,
            analytics_snapshots_generated=usage.analytics_snapshots_generated,
        )


class PlanCatalogEntryPublic(BaseModel):
    plan: Plan
    label: str
    limits: PlanLimitsPublic


class BillingInfoPublic(BaseModel):
    current_plan: Plan
    is_billing_configured: bool
    plans: list[PlanCatalogEntryPublic]


class AuditLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action: str
    actor_user_id: uuid.UUID | None
    target_type: str | None
    target_id: str | None
    ip_address: str | None
    extra: dict[str, object]
    created_at: datetime

    @classmethod
    def from_audit_log(cls, entry: AuditLog) -> "AuditLogPublic":
        return cls.model_validate(entry)
