import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.chat_status import RetrievalSourceType
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, enum_column

if TYPE_CHECKING:
    from app.models.ai_run import AiRun


class RetrievalResult(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One retrieved source cited (or available to be cited) by an AiRun's
    response — the durable record source references are rendered from.

    `file_path`/`start_line`/`end_line`/`symbol_name` are a **snapshot**
    taken at retrieval time, not a live view through `chunk_id` — a later
    re-index deletes and recreates CodeChunk rows (see
    app/indexing/pipeline.py), which would silently invalidate every past
    conversation's citations if this table only stored a foreign key.
    `chunk_id` is kept for a best-effort "jump to current version" link
    and set null (not cascade-deleted) if its chunk is gone.
    """

    __tablename__ = "retrieval_results"

    ai_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[RetrievalSourceType] = mapped_column(
        enum_column(RetrievalSourceType, "retrieval_source_type"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("code_chunks.id", ondelete="SET NULL"), nullable=True
    )
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    symbol_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)

    ai_run: Mapped["AiRun"] = relationship(back_populates="retrieval_results")
