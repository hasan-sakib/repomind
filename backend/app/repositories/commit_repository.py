import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commit import Commit


async def list_recent(
    db: AsyncSession, repository_id: uuid.UUID, *, limit: int = 20
) -> list[Commit]:
    result = await db.execute(
        select(Commit)
        .where(Commit.repository_id == repository_id)
        .order_by(Commit.authored_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def existing_shas(db: AsyncSession, repository_id: uuid.UUID) -> set[str]:
    result = await db.execute(select(Commit.sha).where(Commit.repository_id == repository_id))
    return set(result.scalars().all())


async def get_urls_by_shas(
    db: AsyncSession, *, repository_id: uuid.UUID, shas: set[str]
) -> dict[str, str]:
    """Used to attach a clickable GitHub link to a git-history source
    reference (app/schemas/chat.py) without denormalizing the URL onto
    every RetrievalResult row."""
    if not shas:
        return {}
    result = await db.execute(
        select(Commit.sha, Commit.html_url).where(
            Commit.repository_id == repository_id, Commit.sha.in_(shas)
        )
    )
    return {sha: html_url for sha, html_url in result.all()}


def create(
    db: AsyncSession,
    *,
    repository_id: uuid.UUID,
    sha: str,
    message: str,
    author_name: str | None,
    author_login: str | None,
    html_url: str,
    authored_at: datetime,
) -> Commit:
    commit = Commit(
        repository_id=repository_id,
        sha=sha,
        message=message,
        author_name=author_name,
        author_login=author_login,
        html_url=html_url,
        authored_at=authored_at,
    )
    db.add(commit)
    return commit
