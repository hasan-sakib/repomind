import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.github_installation import GitHubInstallation


async def get_by_github_installation_id(
    db: AsyncSession, github_installation_id: int
) -> GitHubInstallation | None:
    result = await db.execute(
        select(GitHubInstallation).where(
            GitHubInstallation.github_installation_id == github_installation_id
        )
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, installation_id: uuid.UUID) -> GitHubInstallation | None:
    return await db.get(GitHubInstallation, installation_id)


async def list_for_organization(
    db: AsyncSession, organization_id: uuid.UUID
) -> list[GitHubInstallation]:
    result = await db.execute(
        select(GitHubInstallation).where(GitHubInstallation.organization_id == organization_id)
    )
    return list(result.scalars().all())


def create(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    github_installation_id: int,
    account_login: str,
    account_type: str,
) -> GitHubInstallation:
    installation = GitHubInstallation(
        organization_id=organization_id,
        github_installation_id=github_installation_id,
        account_login=account_login,
        account_type=account_type,
    )
    db.add(installation)
    return installation
