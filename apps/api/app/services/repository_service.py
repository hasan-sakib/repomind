import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repository import Repository
from app.domain.repository_status import RepositoryStatus
from app.integrations.github import app_client, rest_client
from app.repositories import (
    audit_log_repository,
    github_installation_repository,
    organization_member_repository,
    repository_membership_repository,
    repository_repository,
)
from app.services.exceptions import (
    InstallationNotFoundError,
    RepositoryAlreadyConnectedError,
    RepositoryNotFoundError,
)


async def require_repository_access(
    db: AsyncSession, *, repository_id: uuid.UUID, user_id: uuid.UUID
) -> Repository:
    membership = await repository_membership_repository.get(
        db, repository_id=repository_id, user_id=user_id
    )
    if membership is None:
        raise RepositoryNotFoundError("Repository not found")
    repository = await repository_repository.get_by_id(db, repository_id)
    if repository is None:
        raise RepositoryNotFoundError("Repository not found")
    return repository


async def list_repositories_for_organization(
    db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID
) -> list[Repository]:
    accessible_ids = set(
        await repository_membership_repository.list_repository_ids_for_user(db, user_id)
    )
    all_repos = await repository_repository.list_for_organization(db, organization_id)
    return [r for r in all_repos if r.id in accessible_ids]


async def connect_repository(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    installation_id: uuid.UUID,
    github_repo_id: int,
    full_name: str,
    actor_user_id: uuid.UUID,
    audit_ip: str | None = None,
) -> Repository:
    installation = await github_installation_repository.get_by_id(db, installation_id)
    if installation is None or installation.organization_id != organization_id:
        raise InstallationNotFoundError("GitHub installation not found")

    if await repository_repository.get_by_github_repo_id(
        db, organization_id=organization_id, github_repo_id=github_repo_id
    ):
        raise RepositoryAlreadyConnectedError("This repository is already connected")

    token = await app_client.get_installation_access_token(installation.github_installation_id)
    repo = await rest_client.get_repository(token, full_name)
    if repo.id != github_repo_id:
        raise RepositoryNotFoundError("Repository not found for this installation")

    repository = repository_repository.create(
        db,
        organization_id=organization_id,
        installation_id=installation.id,
        github_repo_id=repo.id,
        full_name=repo.full_name,
        name=repo.name,
        description=repo.description,
        language=repo.language,
        stargazers_count=repo.stargazers_count,
        forks_count=repo.forks_count,
        default_branch=repo.default_branch,
        private=repo.private,
        html_url=repo.html_url,
    )
    await db.flush()

    members = await organization_member_repository.list_for_organization(db, organization_id)
    for member in members:
        repository_membership_repository.create(
            db, repository_id=repository.id, user_id=member.user_id
        )

    audit_log_repository.create(
        db,
        action="repository.connected",
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        target_type="repository",
        target_id=str(repository.id),
        ip_address=audit_ip,
        extra={"full_name": repository.full_name},
    )
    await db.commit()
    await db.refresh(repository)
    return repository


async def disconnect_repository(
    db: AsyncSession,
    *,
    repository: Repository,
    actor_user_id: uuid.UUID,
    audit_ip: str | None = None,
) -> None:
    audit_log_repository.create(
        db,
        action="repository.disconnected",
        actor_user_id=actor_user_id,
        organization_id=repository.organization_id,
        target_type="repository",
        target_id=str(repository.id),
        ip_address=audit_ip,
        extra={"full_name": repository.full_name},
    )
    await repository_repository.delete(db, repository)
    await db.commit()


def can_start_sync(repository: Repository) -> bool:
    return repository.status != RepositoryStatus.SYNCING
