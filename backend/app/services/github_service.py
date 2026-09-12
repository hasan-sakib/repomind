import uuid
from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.integrations.github import app_client, rest_client
from app.integrations.github.schemas import GitHubRepo
from app.models.github_installation import GitHubInstallation
from app.repositories import github_installation_repository, repository_repository

settings = get_settings()


def build_install_url(*, state: str) -> str:
    params = urlencode({"state": state})
    return f"https://github.com/apps/{settings.github_app_slug}/installations/new?{params}"


async def connect_installation(
    db: AsyncSession, *, organization_id: uuid.UUID, github_installation_id: int
) -> GitHubInstallation:
    """Idempotent: re-running the install flow for an installation already
    linked to this organization just returns the existing row."""
    existing = await github_installation_repository.get_by_github_installation_id(
        db, github_installation_id
    )
    if existing is not None and existing.organization_id == organization_id:
        return existing

    account_login, account_type = await app_client.get_installation_account(github_installation_id)
    installation = github_installation_repository.create(
        db,
        organization_id=organization_id,
        github_installation_id=github_installation_id,
        account_login=account_login,
        account_type=account_type,
    )
    await db.commit()
    await db.refresh(installation)
    return installation


async def list_available_repositories(
    db: AsyncSession, installation: GitHubInstallation
) -> list[GitHubRepo]:
    """All repos the installation can access, minus ones already connected."""
    token = await app_client.get_installation_access_token(installation.github_installation_id)
    all_repos = await rest_client.list_installation_repositories(token)

    connected = await repository_repository.list_by_installation(db, installation.id)
    connected_ids = {r.github_repo_id for r in connected}
    return [r for r in all_repos if r.id not in connected_ids]
