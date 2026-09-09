import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import async_session_factory
from app.domain.repository import Repository
from app.events.publish import publish_notification, publish_state
from app.events.types import EventCategory
from app.integrations.github import app_client, rest_client
from app.repositories import (
    branch_repository,
    commit_repository,
    issue_repository,
    pull_request_repository,
    repository_repository,
)
from app.schemas.github import RepositoryPublic

logger = logging.getLogger("repomind.sync")


async def _publish_sync_status(repository: Repository) -> None:
    await publish_state(
        category=EventCategory.SYNC,
        organization_id=repository.organization_id,
        repository_id=repository.id,
        resource="repository",
        data=RepositoryPublic.from_repository(repository).model_dump(mode="json"),
    )


async def run_sync_in_background(repository_id: uuid.UUID) -> None:
    """Entry point for the `sync_repository` arq task (app/workers/tasks.py).
    Opens its own database session rather than reusing the request's — a
    worker task runs in a separate process after the enqueueing request's
    session has already been closed."""
    async with async_session_factory() as db:
        repository = await db.get(
            Repository, repository_id, options=[selectinload(Repository.installation)]
        )
        if repository is None:
            logger.warning("Repository %s no longer exists; skipping sync", repository_id)
            return
        await sync_repository(db, repository)


async def sync_repository(db: AsyncSession, repository: Repository) -> None:
    """Pulls current metadata, branches, recent commits, pull requests, and
    issues from GitHub into our database. Safe to call repeatedly — every
    step is idempotent (upsert-by-natural-key), so a re-sync after a push
    webhook or a manual "sync now" click never duplicates rows.

    Every step is bounded (see app/integrations/github/rest_client.py) —
    this fetches a recent window, not full history. Runs on the arq worker
    queue (see docs/architecture/0004-codebase-indexing.md for why that
    replaced the FastAPI BackgroundTasks approach from
    docs/architecture/0003-github-integration.md)."""
    repository_repository.mark_syncing(repository)
    await db.commit()
    await _publish_sync_status(repository)

    try:
        token = await app_client.get_installation_access_token(
            repository.installation.github_installation_id
        )
        await _sync_metadata(db, repository, token)
        await _sync_branches(db, repository, token)
        await _sync_commits(db, repository, token)
        await _sync_pull_requests(db, repository, token)
        await _sync_issues(db, repository, token)

        repository_repository.mark_synced(repository, at=datetime.now(UTC))
        await db.commit()
        await _publish_sync_status(repository)
        await publish_notification(
            organization_id=repository.organization_id,
            repository_id=repository.id,
            title=f"{repository.full_name} synced",
            level="success",
        )
    except Exception as exc:  # noqa: BLE001 — must never crash the background task silently
        logger.exception("Sync failed for repository %s", repository.id)
        await db.rollback()
        repository_repository.mark_sync_failed(repository, error=str(exc))
        await db.commit()
        await _publish_sync_status(repository)
        await publish_notification(
            organization_id=repository.organization_id,
            repository_id=repository.id,
            title=f"Sync failed for {repository.full_name}",
            level="error",
        )


async def _sync_metadata(db: AsyncSession, repository: Repository, token: str) -> None:
    repo = await rest_client.get_repository(token, repository.full_name)
    repository.description = repo.description
    repository.language = repo.language
    repository.stargazers_count = repo.stargazers_count
    repository.forks_count = repo.forks_count
    repository.default_branch = repo.default_branch
    await db.flush()


async def _sync_branches(db: AsyncSession, repository: Repository, token: str) -> None:
    branches = await rest_client.list_branches(token, repository.full_name)
    names = [b.name for b in branches]

    for branch in branches:
        existing = await branch_repository.get(db, repository_id=repository.id, name=branch.name)
        is_default = branch.name == repository.default_branch
        if existing is None:
            branch_repository.create(
                db,
                repository_id=repository.id,
                name=branch.name,
                commit_sha=branch.commit_sha,
                is_default=is_default,
            )
        else:
            branch_repository.update(
                existing,
                commit_sha=branch.commit_sha,
                is_default=is_default,
                synced_at=datetime.now(UTC),
            )
    await branch_repository.delete_missing(db, repository_id=repository.id, keep_names=names)
    await db.flush()


async def _sync_commits(db: AsyncSession, repository: Repository, token: str) -> None:
    commits = await rest_client.list_commits(
        token, repository.full_name, branch=repository.default_branch
    )
    existing_shas = await commit_repository.existing_shas(db, repository.id)

    for commit in commits:
        if commit.sha in existing_shas:
            continue
        commit_repository.create(
            db,
            repository_id=repository.id,
            sha=commit.sha,
            message=commit.message,
            author_name=commit.author_name,
            author_login=commit.author_login,
            html_url=commit.html_url,
            authored_at=commit.authored_at,
        )
    await db.flush()


async def _sync_pull_requests(db: AsyncSession, repository: Repository, token: str) -> None:
    pull_requests = await rest_client.list_pull_requests(token, repository.full_name)
    now = datetime.now(UTC)

    for pr in pull_requests:
        existing = await pull_request_repository.get(
            db, repository_id=repository.id, number=pr.number
        )
        if existing is None:
            pull_request_repository.create(
                db,
                repository_id=repository.id,
                number=pr.number,
                title=pr.title,
                state=pr.state,
                author_login=pr.author_login,
                html_url=pr.html_url,
                head_sha=pr.head_sha,
                github_created_at=pr.created_at,
                github_updated_at=pr.updated_at,
                closed_at=pr.closed_at,
                merged_at=pr.merged_at,
                synced_at=now,
            )
        else:
            pull_request_repository.update(
                existing,
                title=pr.title,
                state=pr.state,
                head_sha=pr.head_sha,
                github_updated_at=pr.updated_at,
                closed_at=pr.closed_at,
                merged_at=pr.merged_at,
                synced_at=now,
            )
    await db.flush()


async def _sync_issues(db: AsyncSession, repository: Repository, token: str) -> None:
    issues = await rest_client.list_issues(token, repository.full_name)
    now = datetime.now(UTC)

    for issue in issues:
        existing = await issue_repository.get(db, repository_id=repository.id, number=issue.number)
        if existing is None:
            issue_repository.create(
                db,
                repository_id=repository.id,
                number=issue.number,
                title=issue.title,
                state=issue.state,
                author_login=issue.author_login,
                html_url=issue.html_url,
                github_created_at=issue.created_at,
                github_updated_at=issue.updated_at,
                closed_at=issue.closed_at,
                synced_at=now,
            )
        else:
            issue_repository.update(
                existing,
                title=issue.title,
                state=issue.state,
                github_updated_at=issue.updated_at,
                closed_at=issue.closed_at,
                synced_at=now,
            )
    await db.flush()
