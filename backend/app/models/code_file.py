import uuid
from datetime import datetime
from typing import TYPE_CHECKING, TypedDict

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.code_chunk import CodeChunk
    from app.models.code_symbol import CodeSymbol
    from app.models.repository import Repository


class ImportRecord(TypedDict):
    """One import statement, with the line it appears on — used by
    app/retrieval/dependency_graph.py to give a dependency citation a real
    line number instead of just "somewhere in this file"."""

    text: str
    line: int


class CodeFile(UUIDPrimaryKeyMixin, Base):
    """One row per source file at its most recently indexed commit.
    `content_hash` is the incremental-indexing lever: a re-index that finds
    an unchanged hash skips parsing/chunking/embedding for that file
    entirely — see app/indexing/pipeline.py."""

    __tablename__ = "code_files"
    __table_args__ = (UniqueConstraint("repository_id", "path", name="uq_code_files_repo_path"),)

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    path: Mapped[str] = mapped_column(String(1000), nullable=False)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    imports: Mapped[list[ImportRecord]] = mapped_column(JSONB, nullable=False, default=list)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    repository: Mapped["Repository"] = relationship(back_populates="code_files")
    symbols: Mapped[list["CodeSymbol"]] = relationship(
        back_populates="file", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["CodeChunk"]] = relationship(
        back_populates="file", cascade="all, delete-orphan"
    )
