from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import ArqPool, DbSession, require_csrf_header, require_repository_access
from app.models.repository import Repository
from app.schemas.analytics import AnalyticsSnapshotPublic
from app.services import analytics_service

router = APIRouter(prefix="/repositories/{repository_id}/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsSnapshotPublic)
async def get_snapshot(
    repository: Annotated[Repository, Depends(require_repository_access)],
    db: DbSession,
) -> AnalyticsSnapshotPublic:
    snapshot = await analytics_service.get_latest_snapshot_or_raise(db, repository.id)
    return AnalyticsSnapshotPublic.from_snapshot(snapshot)


@router.post(
    "",
    status_code=202,
    response_model=AnalyticsSnapshotPublic,
    dependencies=[Depends(require_csrf_header)],
)
async def trigger_snapshot(
    repository: Annotated[Repository, Depends(require_repository_access)],
    db: DbSession,
    arq_pool: ArqPool,
    force: bool = False,
) -> AnalyticsSnapshotPublic:
    snapshot, started = await analytics_service.trigger_snapshot_generation(
        db, repository=repository, force=force
    )
    if started:
        await arq_pool.enqueue_job("generate_analytics_snapshot", str(snapshot.id))
    return AnalyticsSnapshotPublic.from_snapshot(snapshot)
