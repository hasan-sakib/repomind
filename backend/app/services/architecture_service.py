import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.architecture import graph_builder
from app.architecture.types import FileDetail, GraphView, SearchResult
from app.domain.repository import Repository
from app.integrations.github import app_client, rest_client
from app.integrations.github.schemas import GitHubCommit
from app.repositories import github_installation_repository
from app.services.exceptions import ArchitectureFileNotFoundError, ArchitecturePackageNotFoundError


async def get_package_graph(db: AsyncSession, repository_id: uuid.UUID) -> GraphView:
    return await graph_builder.build_package_graph(db, repository_id)


async def get_module_graph(db: AsyncSession, repository_id: uuid.UUID, package: str) -> GraphView:
    view = await graph_builder.build_module_graph(db, repository_id, package)
    if not view.nodes:
        raise ArchitecturePackageNotFoundError("No files found in that package")
    return view


async def get_file_detail(
    db: AsyncSession, repository_id: uuid.UUID, file_id: uuid.UUID
) -> FileDetail:
    detail = await graph_builder.get_file_detail(db, repository_id, file_id)
    if detail is None:
        raise ArchitectureFileNotFoundError("File not found")
    return detail


async def search(db: AsyncSession, repository_id: uuid.UUID, query: str) -> list[SearchResult]:
    return await graph_builder.search_nodes(db, repository_id, query)


async def get_recent_changes(
    db: AsyncSession, repository: Repository, *, file_path: str, limit: int = 10
) -> list[GitHubCommit]:
    # Not `repository.installation` — that relationship isn't eager-loaded
    # by require_repository_access, and lazy-loading it here would hit
    # SQLAlchemy's async MissingGreenlet error. installation_id is a plain
    # column already on `repository`, so a second lookup avoids the
    # relationship entirely — same fix as ADR 0003/0004's other
    # installation-token call sites.
    installation = await github_installation_repository.get_by_id(db, repository.installation_id)
    if installation is None:
        return []
    token = await app_client.get_installation_access_token(installation.github_installation_id)
    return await rest_client.list_commits_for_path(
        token,
        repository.full_name,
        branch=repository.default_branch,
        file_path=file_path,
        limit=limit,
    )
