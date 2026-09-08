"""pgvector cosine-similarity search over one repository's code_embeddings
— always repository-scoped (a query never returns another repository's
code) and optionally filtered by language/path substring, the "code
metadata filtering" stage in the architecture."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.chat_status import RetrievalSourceType
from app.domain.code_chunk import CodeChunk
from app.domain.code_embedding import CodeEmbedding
from app.domain.code_file import CodeFile
from app.domain.code_symbol import CodeSymbol
from app.retrieval.types import RetrievedChunk


async def search(
    db: AsyncSession,
    *,
    repository_id: uuid.UUID,
    query_embedding: list[float],
    limit: int,
    path_contains: str | None = None,
) -> list[RetrievedChunk]:
    stmt = (
        select(
            CodeChunk.id,
            CodeChunk.content,
            CodeChunk.start_line,
            CodeChunk.end_line,
            CodeFile.path,
            CodeSymbol.name,
            CodeEmbedding.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .join(CodeEmbedding, CodeEmbedding.chunk_id == CodeChunk.id)
        .join(CodeFile, CodeChunk.file_id == CodeFile.id)
        .outerjoin(CodeSymbol, CodeChunk.symbol_id == CodeSymbol.id)
        .where(CodeFile.repository_id == repository_id)
    )
    if path_contains:
        stmt = stmt.where(CodeFile.path.ilike(f"%{path_contains}%"))
    stmt = stmt.order_by("distance").limit(limit)

    rows = (await db.execute(stmt)).all()
    return [
        RetrievedChunk(
            source_type=RetrievalSourceType.VECTOR,
            chunk_id=chunk_id,
            file_path=path,
            start_line=start_line,
            end_line=end_line,
            symbol_name=symbol_name,
            content=content,
            # pgvector's cosine_distance is 1 - cosine_similarity; report
            # similarity (higher = better) since that's what everything
            # downstream (ranking, the UI's relevance display) expects.
            score=1.0 - distance,
        )
        for chunk_id, content, start_line, end_line, path, symbol_name, distance in rows
    ]
