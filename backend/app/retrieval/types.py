import uuid
from dataclasses import dataclass

from app.domain.chat_status import RetrievalSourceType


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """One candidate piece of context — from vector search, the dependency
    graph, or git history. A common shape so ranking (app/retrieval/
    ranking.py), prompt construction (app/retrieval/prompt.py), and
    persistence (RetrievalResult) don't need to special-case each source."""

    source_type: RetrievalSourceType
    content: str
    # None only for git-history results, which cite a commit, not a file.
    file_path: str | None = None
    chunk_id: uuid.UUID | None = None
    start_line: int | None = None
    end_line: int | None = None
    symbol_name: str | None = None
    commit_sha: str | None = None
    score: float | None = None
