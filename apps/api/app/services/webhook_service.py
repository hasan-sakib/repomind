import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repository import Repository
from app.integrations.github.schemas import GitHubIssue, GitHubPullRequest
from app.repositories import (
    github_installation_repository,
    issue_repository,
    pull_request_repository,
    repository_repository,
    webhook_event_repository,
)

logger = logging.getLogger("repomind.webhooks")


class WebhookResult:
    __slots__ = ("resync_repository_id", "duplicate", "reindex")

    def __init__(
        self,
        resync_repository_id: uuid.UUID | None = None,
        duplicate: bool = False,
        reindex: tuple[uuid.UUID, str] | None = None,
    ):
        self.resync_repository_id = resync_repository_id
        self.duplicate = duplicate
        # (repository_id, commit_sha) for the pushed commit — set only for
        # a push to the default branch, same condition that drives resync.
        self.reindex = reindex


async def _find_repository(
    db: AsyncSession, *, github_installation_id: int, github_repo_id: int
) -> Repository | None:
    installation = await github_installation_repository.get_by_github_installation_id(
        db, github_installation_id
    )
    if installation is None:
        return None
    return await repository_repository.get_by_github_repo_id(
        db, organization_id=installation.organization_id, github_repo_id=github_repo_id
    )


async def process_webhook(
    db: AsyncSession, *, github_delivery_id: str, event_type: str, payload: dict[str, Any]
) -> WebhookResult:
    """Idempotent: a redelivered `github_delivery_id` is detected via the
    unique constraint on webhook_events and skipped without reprocessing —
    see app/domain/webhook_event.py."""
    existing = await webhook_event_repository.get_by_delivery_id(db, github_delivery_id)
    if existing is not None:
        return WebhookResult(duplicate=True)

    event = webhook_event_repository.create(
        db, github_delivery_id=github_delivery_id, event_type=event_type, payload=payload
    )
    try:
        await db.commit()
    except IntegrityError:
        # A concurrent delivery of the same event won the race to insert
        # the webhook_events row first — treat this one as a duplicate too.
        await db.rollback()
        return WebhookResult(duplicate=True)

    try:
        result = await _dispatch(db, event_type=event_type, payload=payload)
        webhook_event_repository.mark_processed(event, at=datetime.now(UTC))
        await db.commit()
        return result
    except Exception:
        logger.exception(
            "Failed to process webhook delivery %s (%s)", github_delivery_id, event_type
        )
        await db.rollback()
        # Re-fetch: the failed transaction above may have rolled back the
        # object's session association along with any pending changes.
        refetched_event = await webhook_event_repository.get_by_delivery_id(db, github_delivery_id)
        if refetched_event is not None:
            webhook_event_repository.mark_failed(
                refetched_event, error="processing error — see server logs", at=datetime.now(UTC)
            )
            await db.commit()
        return WebhookResult()


async def _dispatch(db: AsyncSession, *, event_type: str, payload: dict[str, Any]) -> WebhookResult:
    if event_type == "push":
        return await _handle_push(db, payload)
    if event_type == "pull_request":
        return await _handle_pull_request(db, payload)
    if event_type == "issues":
        return await _handle_issue(db, payload)
    if event_type == "installation":
        return await _handle_installation(db, payload)
    if event_type == "installation_repositories":
        return await _handle_installation_repositories(db, payload)
    logger.info("Ignoring unsupported webhook event type: %s", event_type)
    return WebhookResult()


async def _handle_push(db: AsyncSession, payload: dict[str, Any]) -> WebhookResult:
    ref: str = payload.get("ref", "")
    repository = await _find_repository(
        db,
        github_installation_id=payload["installation"]["id"],
        github_repo_id=payload["repository"]["id"],
    )
    if repository is None:
        return WebhookResult()

    pushed_branch = ref.removeprefix("refs/heads/")
    if pushed_branch != repository.default_branch:
        # Only the default branch drives an automatic resync — pushes to
        # feature branches would otherwise trigger a sync storm.
        return WebhookResult()
    if payload.get("deleted") or not payload.get("after"):
        # A branch deletion push has no real commit to sync/reindex.
        return WebhookResult()
    return WebhookResult(
        resync_repository_id=repository.id, reindex=(repository.id, payload["after"])
    )


async def _handle_pull_request(db: AsyncSession, payload: dict[str, Any]) -> WebhookResult:
    repository = await _find_repository(
        db,
        github_installation_id=payload["installation"]["id"],
        github_repo_id=payload["repository"]["id"],
    )
    if repository is None:
        return WebhookResult()

    pr = GitHubPullRequest.from_api(payload["pull_request"])
    existing = await pull_request_repository.get(db, repository_id=repository.id, number=pr.number)
    now = datetime.now(UTC)
    if existing is None:
        pull_request_repository.create(
            db,
            repository_id=repository.id,
            number=pr.number,
            title=pr.title,
            state=pr.state,
            author_login=pr.author_login,
            html_url=pr.html_url,
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
            github_updated_at=pr.updated_at,
            closed_at=pr.closed_at,
            merged_at=pr.merged_at,
            synced_at=now,
        )
    return WebhookResult()


async def _handle_issue(db: AsyncSession, payload: dict[str, Any]) -> WebhookResult:
    repository = await _find_repository(
        db,
        github_installation_id=payload["installation"]["id"],
        github_repo_id=payload["repository"]["id"],
    )
    if repository is None:
        return WebhookResult()

    issue = GitHubIssue.from_api(payload["issue"])
    existing = await issue_repository.get(db, repository_id=repository.id, number=issue.number)
    now = datetime.now(UTC)
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
    return WebhookResult()


async def _handle_installation(db: AsyncSession, payload: dict[str, Any]) -> WebhookResult:
    action = payload.get("action")
    if action != "deleted":
        # "created" is handled by our own install callback flow, which has
        # the organization context this webhook payload doesn't carry.
        return WebhookResult()

    installation = await github_installation_repository.get_by_github_installation_id(
        db, payload["installation"]["id"]
    )
    if installation is not None:
        await db.delete(installation)  # cascades to repositories and everything under them
    return WebhookResult()


async def _handle_installation_repositories(
    db: AsyncSession, payload: dict[str, Any]
) -> WebhookResult:
    if payload.get("action") != "removed":
        # "added" repos simply become choosable next time the user opens
        # the repository selector — connecting stays a deliberate action.
        return WebhookResult()

    installation = await github_installation_repository.get_by_github_installation_id(
        db, payload["installation"]["id"]
    )
    if installation is None:
        return WebhookResult()

    for repo_ref in payload.get("repositories_removed", []):
        repository = await repository_repository.get_by_github_repo_id(
            db, organization_id=installation.organization_id, github_repo_id=repo_ref["id"]
        )
        if repository is not None:
            await repository_repository.delete(db, repository)
    return WebhookResult()
