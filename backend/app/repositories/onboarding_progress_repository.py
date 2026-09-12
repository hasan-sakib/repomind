import uuid

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.onboarding_progress import OnboardingProgress


async def list_completed_item_keys(
    db: AsyncSession, *, repository_id: uuid.UUID, user_id: uuid.UUID
) -> set[str]:
    result = await db.execute(
        select(OnboardingProgress.item_key).where(
            OnboardingProgress.repository_id == repository_id,
            OnboardingProgress.user_id == user_id,
        )
    )
    return set(result.scalars().all())


async def mark_completed(
    db: AsyncSession, *, repository_id: uuid.UUID, user_id: uuid.UUID, item_key: str
) -> None:
    existing = await db.execute(
        select(OnboardingProgress).where(
            OnboardingProgress.repository_id == repository_id,
            OnboardingProgress.user_id == user_id,
            OnboardingProgress.item_key == item_key,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(OnboardingProgress(repository_id=repository_id, user_id=user_id, item_key=item_key))


async def mark_incomplete(
    db: AsyncSession, *, repository_id: uuid.UUID, user_id: uuid.UUID, item_key: str
) -> None:
    await db.execute(
        sa_delete(OnboardingProgress).where(
            OnboardingProgress.repository_id == repository_id,
            OnboardingProgress.user_id == user_id,
            OnboardingProgress.item_key == item_key,
        )
    )
