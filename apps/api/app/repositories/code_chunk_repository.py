import uuid

from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.code_chunk import CodeChunk


def create(
    db: AsyncSession,
    *,
    file_id: uuid.UUID,
    symbol_id: uuid.UUID | None,
    chunk_type: str,
    content: str,
    start_line: int,
    end_line: int,
    content_hash: str,
    token_count: int,
) -> CodeChunk:
    chunk = CodeChunk(
        file_id=file_id,
        symbol_id=symbol_id,
        chunk_type=chunk_type,
        content=content,
        start_line=start_line,
        end_line=end_line,
        content_hash=content_hash,
        token_count=token_count,
    )
    db.add(chunk)
    return chunk


async def delete_for_file(db: AsyncSession, file_id: uuid.UUID) -> None:
    # code_embeddings.chunk_id has ON DELETE CASCADE, so this also removes
    # the embeddings for every deleted chunk.
    await db.execute(sa_delete(CodeChunk).where(CodeChunk.file_id == file_id))
