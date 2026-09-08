import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.chat_status import RetrievalSourceType
from app.domain.retrieval_result import RetrievalResult


def create(
    db: AsyncSession,
    *,
    ai_run_id: uuid.UUID,
    source_type: RetrievalSourceType,
    rank: int,
    score: float | None,
    chunk_id: uuid.UUID | None,
    file_path: str | None,
    start_line: int | None,
    end_line: int | None,
    symbol_name: str | None,
    commit_sha: str | None,
) -> RetrievalResult:
    row = RetrievalResult(
        ai_run_id=ai_run_id,
        source_type=source_type,
        rank=rank,
        score=score,
        chunk_id=chunk_id,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        symbol_name=symbol_name,
        commit_sha=commit_sha,
    )
    db.add(row)
    return row
