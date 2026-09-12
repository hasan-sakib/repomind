import uuid
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.code_chunk import CodeChunk

# Must match Settings.embedding_dimension (app/core/config.py) and the
# hand-written HNSW index in the Alembic migration. Changing this requires a
# migration plus a full re-embed of every repository, so it is a fixed
# constant rather than a runtime setting read by the domain layer.
EMBEDDING_DIMENSION = 1024


class CodeEmbedding(UUIDPrimaryKeyMixin, Base):
    """One vector per CodeChunk. Kept as its own table (rather than a column
    on code_chunks) so the HNSW index only ever indexes rows that actually
    have an embedding, and so re-embedding with a new model/dimension is a
    row replacement, not a schema change."""

    __tablename__ = "code_embeddings"

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)

    chunk: Mapped["CodeChunk"] = relationship(back_populates="embedding")
