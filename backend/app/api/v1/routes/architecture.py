import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, require_repository_access
from app.models.repository import Repository
from app.schemas.architecture import (
    FileDetailPublic,
    GraphViewPublic,
    RecentCommitPublic,
    SearchResultPublic,
)
from app.services import architecture_service

router = APIRouter(prefix="/repositories/{repository_id}/architecture", tags=["architecture"])


@router.get("/graph", response_model=GraphViewPublic)
async def get_graph(
    repository: Annotated[Repository, Depends(require_repository_access)],
    db: DbSession,
    package: Annotated[str | None, Query()] = None,
) -> GraphViewPublic:
    """No `package` -> the top-level package graph (the initial view).
    `package=<dir path>` -> that package expanded into its files — the
    "progressive expansion" the graph never renders more than one level
    of at a time (see docs/architecture/0006-architecture-dependency-graph.md)."""
    if package is None:
        view = await architecture_service.get_package_graph(db, repository.id)
    else:
        view = await architecture_service.get_module_graph(db, repository.id, package)
    return GraphViewPublic.from_view(view)


@router.get("/files/{file_id}", response_model=FileDetailPublic)
async def get_file_detail(
    repository: Annotated[Repository, Depends(require_repository_access)],
    file_id: uuid.UUID,
    db: DbSession,
) -> FileDetailPublic:
    detail = await architecture_service.get_file_detail(db, repository.id, file_id)
    return FileDetailPublic.from_detail(detail)


@router.get("/files/{file_id}/recent-changes", response_model=list[RecentCommitPublic])
async def get_recent_changes(
    repository: Annotated[Repository, Depends(require_repository_access)],
    file_id: uuid.UUID,
    db: DbSession,
) -> list[RecentCommitPublic]:
    detail = await architecture_service.get_file_detail(db, repository.id, file_id)
    commits = await architecture_service.get_recent_changes(db, repository, file_path=detail.path)
    return [RecentCommitPublic.from_commit(c) for c in commits]


@router.get("/search", response_model=list[SearchResultPublic])
async def search(
    repository: Annotated[Repository, Depends(require_repository_access)],
    db: DbSession,
    q: Annotated[str, Query(min_length=1, max_length=200)],
) -> list[SearchResultPublic]:
    results = await architecture_service.search(db, repository.id, q)
    return [SearchResultPublic.from_result(r) for r in results]
