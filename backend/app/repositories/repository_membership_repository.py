import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.repository_membership import RepositoryMembership


async def get(
    db: AsyncSession, *, repository_id: uuid.UUID, user_id: uuid.UUID
) -> RepositoryMembership | None:
    result = await db.execute(
        select(RepositoryMembership).where(
            RepositoryMembership.repository_id == repository_id,
            RepositoryMembership.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_repository_ids_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    result = await db.execute(
        select(RepositoryMembership.repository_id).where(RepositoryMembership.user_id == user_id)
    )
    return list(result.scalars().all())


async def list_for_repository(
    db: AsyncSession, repository_id: uuid.UUID
) -> list[RepositoryMembership]:
    result = await db.execute(
        select(RepositoryMembership)
        .where(RepositoryMembership.repository_id == repository_id)
        .options(selectinload(RepositoryMembership.user))
    )
    return list(result.scalars().all())


def create(
    db: AsyncSession, *, repository_id: uuid.UUID, user_id: uuid.UUID
) -> RepositoryMembership:
    membership = RepositoryMembership(repository_id=repository_id, user_id=user_id)
    db.add(membership)
    return membership
