import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.repository import Repository
from app.models.repository_status import RepositoryStatus


async def get_by_id(db: AsyncSession, repository_id: uuid.UUID) -> Repository | None:
    return await db.get(Repository, repository_id)


async def count_for_organization(db: AsyncSession, organization_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Repository)
        .where(Repository.organization_id == organization_id)
    )
    return result.scalar_one()


async def get_by_github_repo_id(
    db: AsyncSession, *, organization_id: uuid.UUID, github_repo_id: int
) -> Repository | None:
    result = await db.execute(
        select(Repository).where(
            Repository.organization_id == organization_id,
            Repository.github_repo_id == github_repo_id,
        )
    )
    return result.scalar_one_or_none()


async def list_for_organization(db: AsyncSession, organization_id: uuid.UUID) -> list[Repository]:
    result = await db.execute(
        select(Repository)
        .where(Repository.organization_id == organization_id)
        .order_by(Repository.connected_at.desc())
    )
    return list(result.scalars().all())


async def list_by_installation(db: AsyncSession, installation_id: uuid.UUID) -> list[Repository]:
    result = await db.execute(
        select(Repository)
        .where(Repository.installation_id == installation_id)
        .options(selectinload(Repository.installation))
    )
    return list(result.scalars().all())


def create(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    installation_id: uuid.UUID,
    github_repo_id: int,
    full_name: str,
    name: str,
    description: str | None,
    language: str | None,
    stargazers_count: int,
    forks_count: int,
    default_branch: str,
    private: bool,
    html_url: str,
) -> Repository:
    repository = Repository(
        organization_id=organization_id,
        installation_id=installation_id,
        github_repo_id=github_repo_id,
        full_name=full_name,
        name=name,
        description=description,
        language=language,
        stargazers_count=stargazers_count,
        forks_count=forks_count,
        default_branch=default_branch,
        private=private,
        html_url=html_url,
        status=RepositoryStatus.PENDING,
    )
    db.add(repository)
    return repository


async def delete(db: AsyncSession, repository: Repository) -> None:
    await db.delete(repository)


def mark_syncing(repository: Repository) -> None:
    repository.status = RepositoryStatus.SYNCING
    repository.sync_error = None


def mark_synced(repository: Repository, *, at: datetime) -> None:
    repository.status = RepositoryStatus.READY
    repository.last_synced_at = at
    repository.sync_error = None


def mark_sync_failed(repository: Repository, *, error: str) -> None:
    repository.status = RepositoryStatus.ERROR
    repository.sync_error = error
