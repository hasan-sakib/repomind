import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import (
    DbSession,
    get_current_user,
    require_csrf_header,
    require_organization_role,
)
from app.billing import entitlements
from app.billing.factory import get_billing_provider
from app.billing.plans import PLAN_LABELS, PLAN_LIMITS
from app.billing.usage import get_usage_summary
from app.models.organization_member import OrganizationMember
from app.models.role import Role
from app.models.user import User
from app.repositories import organization_repository
from app.schemas.organization import (
    AddMemberRequest,
    AuditLogPublic,
    BillingInfoPublic,
    MemberPublic,
    OrganizationCreateRequest,
    OrganizationMembershipPublic,
    OrganizationPublic,
    PlanCatalogEntryPublic,
    PlanLimitsPublic,
    SetPlanRequest,
    UpdateMemberRoleRequest,
    UpdateOrganizationRequest,
    UsageSummaryPublic,
)
from app.services import organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("", response_model=list[OrganizationMembershipPublic])
async def list_my_organizations(
    db: DbSession, user: Annotated[User, Depends(get_current_user)]
) -> list[OrganizationMembershipPublic]:
    memberships = await organization_service.list_organizations_for_user(db, user.id)
    return [OrganizationMembershipPublic.from_member(m) for m in memberships]


@router.post(
    "",
    response_model=OrganizationPublic,
    status_code=201,
    dependencies=[Depends(require_csrf_header)],
)
async def create_organization(
    body: OrganizationCreateRequest,
    request: Request,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
) -> OrganizationPublic:
    organization = await organization_service.create_organization(
        db, name=body.name, owner=user, audit_ip=_client_ip(request)
    )
    return OrganizationPublic.from_organization(organization)


@router.get("/{organization_id}", response_model=OrganizationPublic)
async def get_organization(
    member: Annotated[OrganizationMember, Depends(require_organization_role(Role.VIEWER))],
    db: DbSession,
) -> OrganizationPublic:
    organization = await organization_repository.get_by_id(db, member.organization_id)
    assert organization is not None  # FK guarantees this if the membership row exists
    return OrganizationPublic.from_organization(organization)


@router.patch(
    "/{organization_id}",
    response_model=OrganizationPublic,
    dependencies=[Depends(require_csrf_header)],
)
async def update_organization(
    body: UpdateOrganizationRequest,
    request: Request,
    db: DbSession,
    actor: Annotated[OrganizationMember, Depends(require_organization_role(Role.ADMIN))],
) -> OrganizationPublic:
    organization = await organization_service.update_organization(
        db,
        organization_id=actor.organization_id,
        actor=actor,
        name=body.name,
        audit_ip=_client_ip(request),
    )
    return OrganizationPublic.from_organization(organization)


@router.post(
    "/{organization_id}/plan",
    response_model=OrganizationPublic,
    dependencies=[Depends(require_csrf_header)],
)
async def set_plan(
    body: SetPlanRequest,
    request: Request,
    db: DbSession,
    actor: Annotated[OrganizationMember, Depends(require_organization_role(Role.VIEWER))],
) -> OrganizationPublic:
    # Minimum role is VIEWER at the route level (same reasoning as
    # remove_member above) — organization_service.set_plan enforces the
    # real rule (owner-only).
    organization = await organization_service.set_plan(
        db,
        organization_id=actor.organization_id,
        actor=actor,
        plan=body.plan,
        audit_ip=_client_ip(request),
    )
    return OrganizationPublic.from_organization(organization)


@router.get("/{organization_id}/usage", response_model=UsageSummaryPublic)
async def get_usage(
    member: Annotated[OrganizationMember, Depends(require_organization_role(Role.VIEWER))],
    db: DbSession,
) -> UsageSummaryPublic:
    organization = await organization_repository.get_by_id(db, member.organization_id)
    assert organization is not None
    usage = await get_usage_summary(db, organization)
    return UsageSummaryPublic.from_usage(
        plan=organization.plan, limits=entitlements.get_limits(organization), usage=usage
    )


@router.get("/{organization_id}/billing", response_model=BillingInfoPublic)
async def get_billing_info(
    member: Annotated[OrganizationMember, Depends(require_organization_role(Role.VIEWER))],
    db: DbSession,
) -> BillingInfoPublic:
    organization = await organization_repository.get_by_id(db, member.organization_id)
    assert organization is not None
    return BillingInfoPublic(
        current_plan=organization.plan,
        is_billing_configured=get_billing_provider().is_configured,
        plans=[
            PlanCatalogEntryPublic(
                plan=plan, label=PLAN_LABELS[plan], limits=PlanLimitsPublic.from_limits(limits)
            )
            for plan, limits in PLAN_LIMITS.items()
        ],
    )


@router.get("/{organization_id}/audit-logs", response_model=list[AuditLogPublic])
async def get_audit_logs(
    member: Annotated[OrganizationMember, Depends(require_organization_role(Role.ADMIN))],
    db: DbSession,
) -> list[AuditLogPublic]:
    entries = await organization_service.list_audit_logs(db, member.organization_id)
    return [AuditLogPublic.from_audit_log(e) for e in entries]


@router.get("/{organization_id}/members", response_model=list[MemberPublic])
async def list_members(
    organization_id: uuid.UUID,
    db: DbSession,
    _member: Annotated[OrganizationMember, Depends(require_organization_role(Role.VIEWER))],
) -> list[MemberPublic]:
    members = await organization_service.list_members(db, organization_id)
    return [MemberPublic.from_member(m) for m in members]


@router.post(
    "/{organization_id}/members",
    response_model=MemberPublic,
    status_code=201,
    dependencies=[Depends(require_csrf_header)],
)
async def add_member(
    organization_id: uuid.UUID,
    body: AddMemberRequest,
    request: Request,
    db: DbSession,
    actor: Annotated[OrganizationMember, Depends(require_organization_role(Role.ADMIN))],
) -> MemberPublic:
    member = await organization_service.add_member(
        db,
        organization_id=organization_id,
        actor=actor,
        email=body.email,
        role=body.role,
        audit_ip=_client_ip(request),
    )
    await db.refresh(member, attribute_names=["user"])
    return MemberPublic.from_member(member)


@router.patch(
    "/{organization_id}/members/{user_id}",
    response_model=MemberPublic,
    dependencies=[Depends(require_csrf_header)],
)
async def update_member_role(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    body: UpdateMemberRoleRequest,
    request: Request,
    db: DbSession,
    actor: Annotated[OrganizationMember, Depends(require_organization_role(Role.ADMIN))],
) -> MemberPublic:
    member = await organization_service.update_member_role(
        db,
        organization_id=organization_id,
        actor=actor,
        target_user_id=user_id,
        new_role=body.role,
        audit_ip=_client_ip(request),
    )
    await db.refresh(member, attribute_names=["user"])
    return MemberPublic.from_member(member)


@router.delete(
    "/{organization_id}/members/{user_id}",
    status_code=204,
    dependencies=[Depends(require_csrf_header)],
)
async def remove_member(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    request: Request,
    db: DbSession,
    actor: Annotated[OrganizationMember, Depends(require_organization_role(Role.VIEWER))],
) -> None:
    # Minimum role is VIEWER (i.e. just "is a member") at the route level
    # because self-removal must always be allowed regardless of role;
    # organization_service.remove_member enforces the real rule (self is
    # always fine, removing someone else needs admin+, owners are protected).
    await organization_service.remove_member(
        db,
        organization_id=organization_id,
        actor=actor,
        target_user_id=user_id,
        audit_ip=_client_ip(request),
    )
