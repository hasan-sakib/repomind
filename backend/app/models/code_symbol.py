import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.domain.code_file import CodeFile


class CodeSymbol(UUIDPrimaryKeyMixin, Base):
    """A named declaration extracted from a file's AST (function, class,
    method, interface, ...). `parent_symbol_id` links methods to their
    enclosing class so the UI can render nesting without re-parsing."""

    __tablename__ = "code_symbols"

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_symbol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("code_symbols.id", ondelete="CASCADE"), nullable=True
    )
    symbol_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    docstring: Mapped[str | None] = mapped_column(Text, nullable=True)

    file: Mapped["CodeFile"] = relationship(back_populates="symbols")
