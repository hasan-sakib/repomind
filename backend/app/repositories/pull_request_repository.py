import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pull_request import PullRequest


async def list_for_repository(
    db: AsyncSession, repository_id: uuid.UUID, *, state: str | None = None, limit: int = 50
) -> list[PullRequest]:
    stmt = select(PullRequest).where(PullRequest.repository_id == repository_id)
    if state:
        stmt = stmt.where(PullRequest.state == state)
    stmt = stmt.order_by(PullRequest.github_updated_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get(db: AsyncSession, *, repository_id: uuid.UUID, number: int) -> PullRequest | None:
    result = await db.execute(
        select(PullRequest).where(
            PullRequest.repository_id == repository_id, PullRequest.number == number
        )
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
    head_sha: str,
    github_created_at: datetime,
    github_updated_at: datetime,
    closed_at: datetime | None,
    merged_at: datetime | None,
    synced_at: datetime,
) -> PullRequest:
    pr = PullRequest(
        repository_id=repository_id,
        number=number,
        title=title,
        state=state,
        author_login=author_login,
        html_url=html_url,
        head_sha=head_sha,
        github_created_at=github_created_at,
        github_updated_at=github_updated_at,
        closed_at=closed_at,
        merged_at=merged_at,
        synced_at=synced_at,
    )
    db.add(pr)
    return pr


def update(
    pr: PullRequest,
    *,
    title: str,
    state: str,
    head_sha: str,
    github_updated_at: datetime,
    closed_at: datetime | None,
    merged_at: datetime | None,
    synced_at: datetime,
) -> None:
    pr.title = title
    pr.state = state
    pr.head_sha = head_sha
    pr.github_updated_at = github_updated_at
    pr.closed_at = closed_at
    pr.merged_at = merged_at
    pr.synced_at = synced_at
