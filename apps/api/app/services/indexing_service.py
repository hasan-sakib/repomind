import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.indexing_job import IndexingJob
from app.domain.indexing_status import IndexingTrigger
from app.domain.repository import Repository
from app.repositories import branch_repository, indexing_job_repository
from app.services.exceptions import IndexingJobNotFoundError, RepositoryNotSyncedError


async def trigger_indexing(
    db: AsyncSession,
    *,
    repository: Repository,
    trigger: IndexingTrigger,
    commit_sha: str | None = None,
) -> tuple[IndexingJob, bool]:
    """Creates and enqueues an indexing job, unless one is already queued or
    running for this repository — mirrors
    repository_service.can_start_sync's started-boolean contract, but here
    the guard has to be race-safe against two concurrent triggers (a
    "sync now" click racing a push webhook), so it's a DB query rather than
    a field on the in-memory Repository the caller already loaded.

    Returns (job, started); when started is False, `job` is the existing
    active job instead of a new one, so callers can still show the caller
    where progress is being tracked.
    """
    active = await indexing_job_repository.get_active_for_repository(db, repository.id)
    if active is not None:
        return active, False

    resolved_commit_sha = commit_sha
    if resolved_commit_sha is None:
        default_branch = await branch_repository.get(
            db, repository_id=repository.id, name=repository.default_branch
        )
        if default_branch is None:
            raise RepositoryNotSyncedError(
                "Repository has no synced default branch yet — sync it before indexing"
            )
        resolved_commit_sha = default_branch.commit_sha

    job = indexing_job_repository.create(
        db, repository_id=repository.id, trigger=trigger, commit_sha=resolved_commit_sha
    )
    await db.commit()
    return job, True


async def get_job_or_raise(
    db: AsyncSession, *, repository_id: uuid.UUID, job_id: uuid.UUID
) -> IndexingJob:
    job = await indexing_job_repository.get(db, job_id)
    # Same "not found" for a missing job and one that belongs to a
    # different repository — the caller has repository access, not
    # necessarily job access, and a 404 doesn't confirm the job exists
    # elsewhere.
    if job is None or job.repository_id != repository_id:
        raise IndexingJobNotFoundError("Indexing job not found")
    return job
