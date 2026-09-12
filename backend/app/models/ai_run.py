import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.chat_status import AiRunStatus, QueryIntent
from app.domain.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, enum_column

if TYPE_CHECKING:
    from app.domain.retrieval_result import RetrievalResult


class AiRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One query -> retrieve -> generate cycle. `user_message_id` is the
    question being answered; `assistant_message_id` is null until the
    response is persisted. "Regenerate" creates a *new* AiRun pointing at
    the same `user_message_id` with a new `assistant_message_id` — the
    original run and its retrieval_results stay intact for comparison/
    observability rather than being overwritten."""

    __tablename__ = "ai_runs"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    assistant_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[AiRunStatus] = mapped_column(
        enum_column(AiRunStatus, "ai_run_status"), nullable=False, default=AiRunStatus.RUNNING
    )
    intent: Mapped[QueryIntent | None] = mapped_column(
        enum_column(QueryIntent, "query_intent"), nullable=True
    )
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    retrieval_results: Mapped[list["RetrievalResult"]] = relationship(
        back_populates="ai_run", cascade="all, delete-orphan", order_by="RetrievalResult.rank"
    )
