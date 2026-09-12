import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.code_embedding import CodeEmbedding
    from app.models.code_file import CodeFile


class CodeChunk(UUIDPrimaryKeyMixin, Base):
    """The unit that gets embedded. Built by app/indexing/chunker.py from
    AST boundaries (one symbol, or a small group of adjacent small symbols)
    — never a fixed-size character split. `symbol_id` is null for chunks
    that come from prose/fallback splitting of files with no tree-sitter
    grammar (e.g. Markdown)."""

    __tablename__ = "code_chunks"

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("code_symbols.id", ondelete="SET NULL"), nullable=True
    )
    chunk_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)

    file: Mapped["CodeFile"] = relationship(back_populates="chunks")
    embedding: Mapped["CodeEmbedding | None"] = relationship(
        back_populates="chunk", cascade="all, delete-orphan", uselist=False
    )
