import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.slugify import slugify
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.role import Role, role_at_least
from app.models.user import User
from app.repositories import (
    audit_log_repository,
    organization_member_repository,
    organization_repository,
    repository_membership_repository,
    repository_repository,
    user_repository,
)
from app.services.exceptions import (
    InsufficientRoleError,
    LastOwnerError,
    MemberAlreadyExistsError,
    OrganizationNotFoundError,
    UserNotFoundError,
)


async def _unique_slug(db: AsyncSession, base: str) -> str:
    candidate = slugify(base)
    suffix = 0
    while await organization_repository.slug_exists(db, candidate):
        suffix += 1
        candidate = f"{slugify(base)}-{suffix}"
    return candidate


async def create_organization(
    db: AsyncSession, *, name: str, owner: User, audit_ip: str | None = None
) -> Organization:
    slug = await _unique_slug(db, name)
    organization = organization_repository.create(db, name=name, slug=slug)
    await db.flush()
    organization_member_repository.create(
        db, organization_id=organization.id, user_id=owner.id, role=Role.OWNER
    )
    audit_log_repository.create(
        db,
        action="organization.created",
        actor_user_id=owner.id,
        organization_id=organization.id,
        target_type="organization",
        target_id=str(organization.id),
        ip_address=audit_ip,
    )
    await db.commit()
    await db.refresh(organization)
    return organization


async def list_organizations_for_user(
    db: AsyncSession, user_id: uuid.UUID
) -> list[OrganizationMember]:
    """Returns memberships with `.organization` eagerly loaded, so callers
    get both the organization and the caller's role in it."""
    return await organization_member_repository.list_for_user(db, user_id)


async def get_membership_or_raise(
    db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID
) -> OrganizationMember:
    member = await organization_member_repository.get(
        db, organization_id=organization_id, user_id=user_id
    )
    if member is None:
        # Deliberately the same error whether the organization doesn't
        # exist or the caller just isn't a member of it — avoids leaking
        # which organizations exist to users who aren't in them.
        raise OrganizationNotFoundError("Organization not found")
    return member


async def require_role(
    db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID, minimum: Role
) -> OrganizationMember:
    member = await get_membership_or_raise(db, organization_id=organization_id, user_id=user_id)
    if not role_at_least(member.role, minimum):
        raise InsufficientRoleError(f"Requires at least {minimum.value} role")
    return member


async def list_members(db: AsyncSession, organization_id: uuid.UUID) -> list[OrganizationMember]:
    """Returns memberships with `.user` eagerly loaded."""
    return await organization_member_repository.list_for_organization(db, organization_id)


async def add_member(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor: OrganizationMember,
    email: str,
    role: Role,
    audit_ip: str | None = None,
) -> OrganizationMember:
    if role == Role.OWNER and actor.role != Role.OWNER:
        raise InsufficientRoleError("Only an owner can grant the owner role")

    target_user = await user_repository.get_by_email(db, email)
    if target_user is None:
        raise UserNotFoundError(f"No registered user with email {email}")

    existing = await organization_member_repository.get(
        db, organization_id=organization_id, user_id=target_user.id
    )
    if existing is not None:
        raise MemberAlreadyExistsError("User is already a member of this organization")

    member = organization_member_repository.create(
        db, organization_id=organization_id, user_id=target_user.id, role=role
    )
    await db.flush()

    # New members automatically get visibility into every repository
    # already connected to this organization — see
    # app/models/repository_membership.py for why this is auto-maintained
    # rather than manually managed in this phase.
    for repository in await repository_repository.list_for_organization(db, organization_id):
        repository_membership_repository.create(
            db, repository_id=repository.id, user_id=target_user.id
        )

    audit_log_repository.create(
        db,
        action="organization.member.added",
        actor_user_id=actor.user_id,
        organization_id=organization_id,
        target_type="user",
        target_id=str(target_user.id),
        ip_address=audit_ip,
        extra={"role": role.value},
    )
    await db.commit()
    await db.refresh(member)
    return member


async def update_member_role(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor: OrganizationMember,
    target_user_id: uuid.UUID,
    new_role: Role,
    audit_ip: str | None = None,
) -> OrganizationMember:
    target = await get_membership_or_raise(
        db, organization_id=organization_id, user_id=target_user_id
    )

    if (target.role == Role.OWNER or new_role == Role.OWNER) and actor.role != Role.OWNER:
        raise InsufficientRoleError("Only an owner can change an owner's role or grant it")

    if target.role == Role.OWNER and new_role != Role.OWNER:
        owner_count = await organization_member_repository.count_with_role(
            db, organization_id=organization_id, role=Role.OWNER
        )
        if owner_count <= 1:
            raise LastOwnerError("Cannot demote the organization's last owner")

    target.role = new_role
    audit_log_repository.create(
        db,
        action="organization.member.role_changed",
        actor_user_id=actor.user_id,
        organization_id=organization_id,
        target_type="user",
        target_id=str(target_user_id),
        ip_address=audit_ip,
        extra={"role": new_role.value},
    )
    await db.commit()
    await db.refresh(target)
    return target


async def remove_member(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor: OrganizationMember,
    target_user_id: uuid.UUID,
    audit_ip: str | None = None,
) -> None:
    target = await get_membership_or_raise(
        db, organization_id=organization_id, user_id=target_user_id
    )

    is_self_removal = actor.user_id == target_user_id
    if target.role == Role.OWNER:
        owner_count = await organization_member_repository.count_with_role(
            db, organization_id=organization_id, role=Role.OWNER
        )
        if owner_count <= 1:
            raise LastOwnerError("Cannot remove the organization's last owner")
        if not is_self_removal and actor.role != Role.OWNER:
            raise InsufficientRoleError("Only an owner can remove another owner")
    elif not is_self_removal and not role_at_least(actor.role, Role.ADMIN):
        raise InsufficientRoleError("Requires at least admin role")

    await organization_member_repository.delete(db, target)
    audit_log_repository.create(
        db,
        action="organization.member.removed",
        actor_user_id=actor.user_id,
        organization_id=organization_id,
        target_type="user",
        target_id=str(target_user_id),
        ip_address=audit_ip,
    )
    await db.commit()
