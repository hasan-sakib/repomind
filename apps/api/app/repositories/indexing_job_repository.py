import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.indexing_job import IndexingJob
from app.domain.indexing_status import IndexingJobStatus, IndexingStage, IndexingTrigger

_ACTIVE_STATUSES = (IndexingJobStatus.QUEUED, IndexingJobStatus.RUNNING)


async def get(db: AsyncSession, job_id: uuid.UUID) -> IndexingJob | None:
    result = await db.execute(
        select(IndexingJob)
        .options(selectinload(IndexingJob.errors))
        .where(IndexingJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def get_active_for_repository(
    db: AsyncSession, repository_id: uuid.UUID
) -> IndexingJob | None:
    result = await db.execute(
        select(IndexingJob).where(
            IndexingJob.repository_id == repository_id,
            IndexingJob.status.in_(_ACTIVE_STATUSES),
        )
    )
    return result.scalar_one_or_none()


async def list_for_repository(
    db: AsyncSession, repository_id: uuid.UUID, *, limit: int = 20
) -> list[IndexingJob]:
    result = await db.execute(
        select(IndexingJob)
        .options(selectinload(IndexingJob.errors))
        .where(IndexingJob.repository_id == repository_id)
        .order_by(IndexingJob.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def create(
    db: AsyncSession, *, repository_id: uuid.UUID, trigger: IndexingTrigger, commit_sha: str
) -> IndexingJob:
    job = IndexingJob(
        repository_id=repository_id,
        trigger=trigger,
        commit_sha=commit_sha,
        status=IndexingJobStatus.QUEUED,
    )
    db.add(job)
    return job


def mark_running(job: IndexingJob, *, started_at: datetime) -> None:
    job.status = IndexingJobStatus.RUNNING
    job.started_at = started_at


def update_progress(
    job: IndexingJob,
    *,
    current_stage: IndexingStage,
    files_discovered: int | None = None,
    files_processed: int | None = None,
    files_skipped: int | None = None,
    symbols_extracted: int | None = None,
    chunks_created: int | None = None,
    embeddings_generated: int | None = None,
) -> None:
    job.current_stage = current_stage
    if files_discovered is not None:
        job.files_discovered = files_discovered
    if files_processed is not None:
        job.files_processed = files_processed
    if files_skipped is not None:
        job.files_skipped = files_skipped
    if symbols_extracted is not None:
        job.symbols_extracted = symbols_extracted
    if chunks_created is not None:
        job.chunks_created = chunks_created
    if embeddings_generated is not None:
        job.embeddings_generated = embeddings_generated


def mark_finished(
    job: IndexingJob, *, status: IndexingJobStatus, finished_at: datetime, error: str | None = None
) -> None:
    job.status = status
    job.current_stage = IndexingStage.DONE
    job.finished_at = finished_at
    job.error = error
