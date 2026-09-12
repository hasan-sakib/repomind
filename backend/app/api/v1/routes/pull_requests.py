from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import ArqPool, DbSession, require_csrf_header, require_repository_access
from app.domain.repository import Repository
from app.schemas.github import PullRequestPublic
from app.schemas.pr_analysis import PullRequestAnalysisPublic
from app.services import pr_analysis_service

router = APIRouter(prefix="/repositories/{repository_id}/pull-requests", tags=["pull-requests"])


@router.get("/{number}", response_model=PullRequestPublic)
async def get_pull_request(
    repository: Annotated[Repository, Depends(require_repository_access)],
    number: int,
    db: DbSession,
) -> PullRequestPublic:
    pr = await pr_analysis_service.get_pull_request_or_raise(
        db, repository_id=repository.id, number=number
    )
    return PullRequestPublic.from_pull_request(pr)


@router.get("/{number}/analysis", response_model=PullRequestAnalysisPublic)
async def get_analysis(
    repository: Annotated[Repository, Depends(require_repository_access)],
    number: int,
    db: DbSession,
) -> PullRequestAnalysisPublic:
    pr = await pr_analysis_service.get_pull_request_or_raise(
        db, repository_id=repository.id, number=number
    )
    analysis = await pr_analysis_service.get_latest_analysis_or_raise(db, pull_request_id=pr.id)
    return PullRequestAnalysisPublic.from_analysis(analysis)


@router.post(
    "/{number}/analysis",
    status_code=202,
    response_model=PullRequestAnalysisPublic,
    dependencies=[Depends(require_csrf_header)],
)
async def trigger_analysis(
    repository: Annotated[Repository, Depends(require_repository_access)],
    number: int,
    db: DbSession,
    arq_pool: ArqPool,
    force: Annotated[bool, Query()] = False,
) -> PullRequestAnalysisPublic:
    pr = await pr_analysis_service.get_pull_request_or_raise(
        db, repository_id=repository.id, number=number
    )
    analysis, started = await pr_analysis_service.trigger_analysis(db, pull_request=pr, force=force)
    if started:
        await arq_pool.enqueue_job("analyze_pull_request", str(analysis.id))
    return PullRequestAnalysisPublic.from_analysis(analysis)
