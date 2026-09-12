import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.issue import Issue


async def list_for_repository(
    db: AsyncSession, repository_id: uuid.UUID, *, state: str | None = None, limit: int = 50
) -> list[Issue]:
    stmt = select(Issue).where(Issue.repository_id == repository_id)
    if state:
        stmt = stmt.where(Issue.state == state)
    stmt = stmt.order_by(Issue.github_updated_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get(db: AsyncSession, *, repository_id: uuid.UUID, number: int) -> Issue | None:
    result = await db.execute(
        select(Issue).where(Issue.repository_id == repository_id, Issue.number == number)
    )
    return result.scalar_one_or_none()


def create(
    db: AsyncSession,
    *,
    repository_id: uuid.UUID,
    number: int,
    title: str,
    state: str,
    author_login: str | None,
    html_url: str,
    github_created_at: datetime,
    github_updated_at: datetime,
    closed_at: datetime | None,
    synced_at: datetime,
) -> Issue:
    issue = Issue(
        repository_id=repository_id,
        number=number,
        title=title,
        state=state,
        author_login=author_login,
        html_url=html_url,
        github_created_at=github_created_at,
        github_updated_at=github_updated_at,
        closed_at=closed_at,
        synced_at=synced_at,
    )
    db.add(issue)
    return issue


def update(
    issue: Issue,
    *,
    title: str,
    state: str,
    github_updated_at: datetime,
    closed_at: datetime | None,
    synced_at: datetime,
) -> None:
    issue.title = title
    issue.state = state
    issue.github_updated_at = github_updated_at
    issue.closed_at = closed_at
    issue.synced_at = synced_at
