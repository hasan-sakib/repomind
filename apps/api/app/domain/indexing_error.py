import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.indexing_status import IndexingStage
from app.domain.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, enum_column

if TYPE_CHECKING:
    from app.domain.indexing_job import IndexingJob


class IndexingError(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A non-fatal error surfaced to the indexing screen (e.g. one file
    failed to parse). Does not necessarily fail the job — see
    IndexingJobStatus.PARTIAL."""

    __tablename__ = "indexing_errors"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("indexing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    stage: Mapped[IndexingStage] = mapped_column(
        enum_column(IndexingStage, "indexing_stage"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)

    job: Mapped["IndexingJob"] = relationship(back_populates="errors")
