"""Git history as a retrieval source — keyword search over synced commit
messages (app/domain/commit.py). Commits are synced as a bounded recent
window with no per-commit changed-file list (see ADR 0003), so this
cannot answer "which commits touched file X" — only "which recent commits
mention topic X", surfaced as supplementary context/citations for HISTORY-
intent queries. A real file-level history search would need per-commit
diffs fetched from GitHub, deliberately out of scope here — see
docs/architecture/0005-ai-rag-engine.md.
"""

import re
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.chat_status import RetrievalSourceType
from app.domain.commit import Commit
from app.retrieval.types import RetrievedChunk

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}")
_STOPWORDS = {
    "the",
    "and",
    "for",
    "was",
    "were",
    "did",
    "does",
    "how",
    "why",
    "when",
    "this",
    "that",
}


def _keywords(query: str) -> list[str]:
    return [w for w in _WORD.findall(query.lower()) if w not in _STOPWORDS][:5]


async def search_commits(
    db: AsyncSession, *, repository_id: uuid.UUID, query: str, limit: int
) -> list[RetrievedChunk]:
    keywords = _keywords(query)
    if not keywords:
        return []

    stmt = (
        select(Commit)
        .where(
            Commit.repository_id == repository_id,
            or_(*(Commit.message.ilike(f"%{kw}%") for kw in keywords)),
        )
        .order_by(Commit.authored_at.desc())
        .limit(limit)
    )
    commits = (await db.execute(stmt)).scalars().all()
    return [
        RetrievedChunk(
            source_type=RetrievalSourceType.GIT_HISTORY,
            # No file path — a commit citation, not a code citation. The
            # commit's own html_url is looked up from `commit_sha` at
            # response-serialization time (app/services/chat_service.py),
            # not duplicated onto every RetrievedChunk here.
            file_path=None,
            content=(
                f"{commit.message}\n(by {commit.author_login or commit.author_name or 'unknown'})"
            ),
            commit_sha=commit.sha,
            score=None,
        )
        for commit in commits
    ]
