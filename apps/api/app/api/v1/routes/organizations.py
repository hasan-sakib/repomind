import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import (
    DbSession,
    get_current_user,
    require_csrf_header,
    require_organization_role,
)
from app.domain.organization_member import OrganizationMember
from app.domain.role import Role
from app.domain.user import User
from app.repositories import organization_repository
from app.schemas.organization import (
    AddMemberRequest,
    MemberPublic,
    OrganizationCreateRequest,
    OrganizationMembershipPublic,
    OrganizationPublic,
    UpdateMemberRoleRequest,
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
    member: Annotated[
        OrganizationMember, Depends(require_organization_role(Role.VIEWER))
    ],
    db: DbSession,
) -> OrganizationPublic:
    organization = await organization_repository.get_by_id(db, member.organization_id)
    assert organization is not None  # FK guarantees this if the membership row exists
    return OrganizationPublic.from_organization(organization)


@router.get("/{organization_id}/members", response_model=list[MemberPublic])
async def list_members(
    organization_id: uuid.UUID,
    db: DbSession,
    _member: Annotated[
        OrganizationMember, Depends(require_organization_role(Role.VIEWER))
    ],
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
    actor: Annotated[
        OrganizationMember, Depends(require_organization_role(Role.ADMIN))
    ],
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
    actor: Annotated[
        OrganizationMember, Depends(require_organization_role(Role.ADMIN))
    ],
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
    actor: Annotated[
        OrganizationMember, Depends(require_organization_role(Role.VIEWER))
    ],
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
