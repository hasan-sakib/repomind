import uuid
from datetime import datetime

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Branch


async def list_for_repository(db: AsyncSession, repository_id: uuid.UUID) -> list[Branch]:
    result = await db.execute(
        select(Branch).where(Branch.repository_id == repository_id).order_by(Branch.name)
    )
    return list(result.scalars().all())


async def get(db: AsyncSession, *, repository_id: uuid.UUID, name: str) -> Branch | None:
    result = await db.execute(
        select(Branch).where(Branch.repository_id == repository_id, Branch.name == name)
    )
    return result.scalar_one_or_none()


def create(
    db: AsyncSession,
    *,
    repository_id: uuid.UUID,
    name: str,
    commit_sha: str,
    is_default: bool,
) -> Branch:
    branch = Branch(
        repository_id=repository_id, name=name, commit_sha=commit_sha, is_default=is_default
    )
    db.add(branch)
    return branch


def update(branch: Branch, *, commit_sha: str, is_default: bool, synced_at: datetime) -> None:
    branch.commit_sha = commit_sha
    branch.is_default = is_default
    branch.synced_at = synced_at


async def delete_missing(
    db: AsyncSession, *, repository_id: uuid.UUID, keep_names: list[str]
) -> None:
    """Removes branches that no longer exist on GitHub (deleted since the
    last sync)."""
    stmt = sa_delete(Branch).where(Branch.repository_id == repository_id)
    if keep_names:
        stmt = stmt.where(Branch.name.notin_(keep_names))
    await db.execute(stmt)
