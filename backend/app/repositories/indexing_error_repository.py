import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.indexing_error import IndexingError
from app.domain.indexing_status import IndexingStage


def create(
    db: AsyncSession,
    *,
    job_id: uuid.UUID,
    file_path: str | None,
    stage: IndexingStage,
    message: str,
) -> IndexingError:
    error = IndexingError(job_id=job_id, file_path=file_path, stage=stage, message=message)
    db.add(error)
    return error
