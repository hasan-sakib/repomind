import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import (
    ArqPool,
    DbSession,
    get_current_user,
    require_csrf_header,
    require_organization_role,
    require_repository_access,
)
from app.domain.indexing_status import IndexingTrigger
from app.domain.organization_member import OrganizationMember
from app.domain.repository import Repository
from app.domain.role import Role, role_at_least
from app.domain.user import User
from app.repositories import (
    branch_repository,
    commit_repository,
    indexing_job_repository,
    issue_repository,
    pull_request_repository,
)
from app.schemas.github import (
    BranchPublic,
    CommitPublic,
    ConnectRepositoryRequest,
    IssuePublic,
    PullRequestPublic,
    RepositoryOverview,
    RepositoryPublic,
)
from app.schemas.indexing import IndexingJobPublic, TriggerIndexingResponse
from app.services import indexing_service, organization_service, repository_service
from app.services.exceptions import InsufficientRoleError

org_router = APIRouter(
    prefix="/organizations/{organization_id}/repositories", tags=["repositories"]
)
router = APIRouter(prefix="/repositories", tags=["repositories"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@org_router.get("", response_model=list[RepositoryPublic])
async def list_repositories(
    organization_id: uuid.UUID,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
    _actor: Annotated[OrganizationMember, Depends(require_organization_role(Role.VIEWER))],
) -> list[RepositoryPublic]:
    repos = await repository_service.list_repositories_for_organization(
        db, organization_id=organization_id, user_id=user.id
    )
    return [RepositoryPublic.from_repository(r) for r in repos]


@org_router.post(
    "",
    response_model=RepositoryPublic,
    status_code=201,
    dependencies=[Depends(require_csrf_header)],
)
async def connect_repository(
    organization_id: uuid.UUID,
    body: ConnectRepositoryRequest,
    request: Request,
    arq_pool: ArqPool,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
    _actor: Annotated[OrganizationMember, Depends(require_organization_role(Role.ADMIN))],
) -> RepositoryPublic:
    repository = await repository_service.connect_repository(
        db,
        organization_id=organization_id,
        installation_id=body.installation_id,
        github_repo_id=body.github_repo_id,
        full_name=body.full_name,
        actor_user_id=user.id,
        audit_ip=_client_ip(request),
    )
    await arq_pool.enqueue_job("sync_repository", str(repository.id))
    return RepositoryPublic.from_repository(repository)


@router.get("/{repository_id}", response_model=RepositoryOverview)
async def get_repository_overview(
    repository: Annotated[Repository, Depends(require_repository_access)],
    db: DbSession,
) -> RepositoryOverview:
    recent_commits = await commit_repository.list_recent(db, repository.id, limit=10)
    open_prs = await pull_request_repository.list_for_repository(
        db, repository.id, state="open", limit=10
    )
    open_issues = await issue_repository.list_for_repository(
        db, repository.id, state="open", limit=10
    )
    return RepositoryOverview(
        repository=RepositoryPublic.from_repository(repository),
        recent_commits=[CommitPublic.from_commit(c) for c in recent_commits],
        open_pull_requests=[PullRequestPublic.from_pull_request(p) for p in open_prs],
        open_issues=[IssuePublic.from_issue(i) for i in open_issues],
    )


@router.post("/{repository_id}/sync", status_code=202, dependencies=[Depends(require_csrf_header)])
async def sync_repository_now(
    repository: Annotated[Repository, Depends(require_repository_access)],
    arq_pool: ArqPool,
) -> dict[str, bool]:
    started = repository_service.can_start_sync(repository)
    if started:
        await arq_pool.enqueue_job("sync_repository", str(repository.id))
    return {"started": started}


@router.post(
    "/{repository_id}/indexing-jobs",
    status_code=202,
    response_model=TriggerIndexingResponse,
    dependencies=[Depends(require_csrf_header)],
)
async def trigger_indexing_now(
    repository: Annotated[Repository, Depends(require_repository_access)],
    db: DbSession,
    arq_pool: ArqPool,
) -> TriggerIndexingResponse:
    job, started = await indexing_service.trigger_indexing(
        db, repository=repository, trigger=IndexingTrigger.MANUAL
    )
    if started:
        await arq_pool.enqueue_job("index_repository", str(job.id))
    return TriggerIndexingResponse(started=started, job=IndexingJobPublic.from_job(job))


@router.get("/{repository_id}/indexing-jobs", response_model=list[IndexingJobPublic])
async def list_indexing_jobs(
    repository: Annotated[Repository, Depends(require_repository_access)],
    db: DbSession,
) -> list[IndexingJobPublic]:
    jobs = await indexing_job_repository.list_for_repository(db, repository.id)
    return [IndexingJobPublic.from_job(j) for j in jobs]


@router.get(
    "/{repository_id}/indexing-jobs/{job_id}",
    response_model=IndexingJobPublic,
)
async def get_indexing_job(
    repository: Annotated[Repository, Depends(require_repository_access)],
    job_id: uuid.UUID,
    db: DbSession,
) -> IndexingJobPublic:
    job = await indexing_service.get_job_or_raise(db, repository_id=repository.id, job_id=job_id)
    return IndexingJobPublic.from_job(job)


@router.delete("/{repository_id}", status_code=204, dependencies=[Depends(require_csrf_header)])
async def disconnect_repository(
    repository: Annotated[Repository, Depends(require_repository_access)],
    request: Request,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    actor = await organization_service.get_membership_or_raise(
        db, organization_id=repository.organization_id, user_id=user.id
    )
    if not role_at_least(actor.role, Role.ADMIN):
        raise InsufficientRoleError("Requires at least admin role")
    await repository_service.disconnect_repository(
        db, repository=repository, actor_user_id=user.id, audit_ip=_client_ip(request)
    )


@router.get("/{repository_id}/branches", response_model=list[BranchPublic])
async def list_branches(
    repository: Annotated[Repository, Depends(require_repository_access)],
    db: DbSession,
) -> list[BranchPublic]:
    branches = await branch_repository.list_for_repository(db, repository.id)
    return [BranchPublic.from_branch(b) for b in branches]


@router.get("/{repository_id}/commits", response_model=list[CommitPublic])
async def list_commits(
    repository: Annotated[Repository, Depends(require_repository_access)],
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[CommitPublic]:
    commits = await commit_repository.list_recent(db, repository.id, limit=limit)
    return [CommitPublic.from_commit(c) for c in commits]


@router.get("/{repository_id}/pull-requests", response_model=list[PullRequestPublic])
async def list_pull_requests(
    repository: Annotated[Repository, Depends(require_repository_access)],
    db: DbSession,
    state: Annotated[str | None, Query(pattern="^(open|closed)$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[PullRequestPublic]:
    prs = await pull_request_repository.list_for_repository(
        db, repository.id, state=state, limit=limit
    )
    return [PullRequestPublic.from_pull_request(p) for p in prs]


@router.get("/{repository_id}/issues", response_model=list[IssuePublic])
async def list_issues(
    repository: Annotated[Repository, Depends(require_repository_access)],
    db: DbSession,
    state: Annotated[str | None, Query(pattern="^(open|closed)$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[IssuePublic]:
    issues = await issue_repository.list_for_repository(db, repository.id, state=state, limit=limit)
    return [IssuePublic.from_issue(i) for i in issues]
