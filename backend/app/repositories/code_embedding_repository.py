import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code_embedding import CodeEmbedding


def create(
    db: AsyncSession, *, chunk_id: uuid.UUID, embedding: list[float], model: str
) -> CodeEmbedding:
    row = CodeEmbedding(chunk_id=chunk_id, embedding=embedding, model=model)
    db.add(row)
    return row
