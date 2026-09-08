import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.organization_member import OrganizationMember
from app.domain.role import Role


async def get(
    db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID
) -> OrganizationMember | None:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[OrganizationMember]:
    result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == user_id)
        .options(selectinload(OrganizationMember.organization))
        .order_by(OrganizationMember.created_at)
    )
    return list(result.scalars().all())


async def list_for_organization(
    db: AsyncSession, organization_id: uuid.UUID
) -> list[OrganizationMember]:
    result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == organization_id)
        .options(selectinload(OrganizationMember.user))
        .order_by(OrganizationMember.created_at)
    )
    return list(result.scalars().all())


async def count_with_role(
    db: AsyncSession, *, organization_id: uuid.UUID, role: Role
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(OrganizationMember)
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role == role,
        )
    )
    return result.scalar_one()


def create(
    db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID, role: Role
) -> OrganizationMember:
    member = OrganizationMember(organization_id=organization_id, user_id=user_id, role=role)
    db.add(member)
    return member


async def delete(db: AsyncSession, member: OrganizationMember) -> None:
    await db.delete(member)
