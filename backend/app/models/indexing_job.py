import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.indexing_status import IndexingJobStatus, IndexingStage, IndexingTrigger
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, enum_column

if TYPE_CHECKING:
    from app.models.indexing_error import IndexingError


class IndexingJob(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One row per indexing run. Progress fields are updated incrementally
    *during* the run (not just at the end) so polling reflects genuine
    progress — see app/indexing/pipeline.py and
    docs/architecture/0004-codebase-indexing.md."""

    __tablename__ = "indexing_jobs"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[IndexingJobStatus] = mapped_column(
        enum_column(IndexingJobStatus, "indexing_job_status"),
        nullable=False,
        default=IndexingJobStatus.QUEUED,
    )
    trigger: Mapped[IndexingTrigger] = mapped_column(
        enum_column(IndexingTrigger, "indexing_trigger"), nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    current_stage: Mapped[IndexingStage | None] = mapped_column(
        enum_column(IndexingStage, "indexing_stage"), nullable=True
    )

    files_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    symbols_extracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunks_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embeddings_generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    errors: Mapped[list["IndexingError"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
