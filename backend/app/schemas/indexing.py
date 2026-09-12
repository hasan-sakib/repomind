import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.indexing_error import IndexingError
from app.models.indexing_job import IndexingJob
from app.models.indexing_status import IndexingJobStatus, IndexingStage, IndexingTrigger


class IndexingErrorPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_path: str | None
    stage: IndexingStage
    message: str
    created_at: datetime

    @classmethod
    def from_error(cls, error: IndexingError) -> "IndexingErrorPublic":
        return cls.model_validate(error)


class IndexingJobPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    status: IndexingJobStatus
    trigger: IndexingTrigger
    commit_sha: str
    current_stage: IndexingStage | None
    files_discovered: int
    files_processed: int
    files_skipped: int
    symbols_extracted: int
    chunks_created: int
    embeddings_generated: int
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    created_at: datetime
    errors: list[IndexingErrorPublic] = []

    @classmethod
    def from_job(cls, job: IndexingJob) -> "IndexingJobPublic":
        return cls.model_validate(job)


class TriggerIndexingResponse(BaseModel):
    started: bool
    job: IndexingJobPublic
