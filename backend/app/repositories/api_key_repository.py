import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.api_key import ApiKey
from app.models.role import Role


async def get(db: AsyncSession, api_key_id: uuid.UUID) -> ApiKey | None:
    return await db.get(ApiKey, api_key_id)


async def get_by_hash(db: AsyncSession, key_hash: str) -> ApiKey | None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash).options(selectinload(ApiKey.organization))
    )
    return result.scalar_one_or_none()


async def list_for_organization(db: AsyncSession, organization_id: uuid.UUID) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.organization_id == organization_id)
        .options(selectinload(ApiKey.created_by))
        .order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


def create(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    name: str,
    key_prefix: str,
    key_hash: str,
    role: Role,
) -> ApiKey:
    api_key = ApiKey(
        organization_id=organization_id,
        created_by_user_id=created_by_user_id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        role=role,
    )
    db.add(api_key)
    return api_key


def mark_used(api_key: ApiKey, *, at: datetime) -> None:
    api_key.last_used_at = at


def revoke(api_key: ApiKey, *, at: datetime) -> None:
    api_key.revoked_at = at
