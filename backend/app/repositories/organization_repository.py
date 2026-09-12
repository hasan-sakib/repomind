import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization


async def get_by_id(db: AsyncSession, organization_id: uuid.UUID) -> Organization | None:
    return await db.get(Organization, organization_id)


async def slug_exists(db: AsyncSession, slug: str) -> bool:
    result = await db.execute(select(Organization.id).where(Organization.slug == slug))
    return result.scalar_one_or_none() is not None


def create(db: AsyncSession, *, name: str, slug: str) -> Organization:
    organization = Organization(name=name, slug=slug)
    db.add(organization)
    return organization
