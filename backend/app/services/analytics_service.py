"""Orchestrates engineering-analytics snapshot generation: trigger
(create-or-return-cached) and the actual work run by the
`generate_analytics_snapshot` arq task (app/workers/tasks.py). Unlike PR
analysis and onboarding (ADR 0007/0008), no LLM is involved anywhere here
— every field is a computed aggregate over real commit/PR/issue data,
some of it fetched live from GitHub (a deeper commit history, and each
sampled commit's own file diff) because Commit rows alone can't answer
"what changed" or "how often" at the depth a trend chart needs. See
docs/architecture/0009-engineering-analytics.md.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analytics import commits as commits_analytics
from app.analytics import contributors as contributors_analytics
from app.analytics import hotspots as hotspots_analytics
from app.analytics import issues as issues_analytics
from app.analytics import pull_requests as pr_analytics
from app.architecture.graph_builder import rank_files_by_dependents
from app.core.config import Settings, get_settings
from app.db.session import async_session_factory
from app.events.publish import publish_notification, publish_state
from app.events.types import EventCategory
from app.integrations.github import app_client, rest_client
from app.integrations.github.schemas import GitHubPullRequestFile
from app.models.analytics_snapshot import AnalyticsSnapshot, DailyPRIssueRecord
from app.models.repository import Repository
from app.repositories import (
    analytics_snapshot_repository,
    github_installation_repository,
    issue_repository,
    pull_request_repository,
)
from app.schemas.analytics import AnalyticsSnapshotPublic
from app.services.exceptions import AnalyticsSnapshotNotFoundError, RepositoryNotSyncedError

logger = logging.getLogger("repomind.analytics")

_HOTSPOT_FETCH_CONCURRENCY = 10
_MAX_CYCLE_TIME_SAMPLES = 10
_MAX_STALE_ISSUES = 10


async def get_latest_snapshot_or_raise(
    db: AsyncSession, repository_id: uuid.UUID
) -> AnalyticsSnapshot:
    snapshot = await analytics_snapshot_repository.get_latest_for_repository(db, repository_id)
    if snapshot is None:
        raise AnalyticsSnapshotNotFoundError(
            "No analytics have been generated for this repository yet"
        )
    return snapshot


async def trigger_snapshot_generation(
    db: AsyncSession, *, repository: Repository, force: bool = False
) -> tuple[AnalyticsSnapshot, bool]:
    """Returns (snapshot, started). Unlike PR analysis/onboarding, a
    snapshot is never auto-invalidated by a new sync — generation makes
    on the order of a hundred GitHub API calls, so regeneration only ever
    happens on an explicit `force=True`, never silently."""
    if repository.last_synced_at is None:
        raise RepositoryNotSyncedError("Sync this repository before generating analytics")

    latest = await analytics_snapshot_repository.get_latest_for_repository(db, repository.id)
    if latest is not None and not force:
        if analytics_snapshot_repository.is_active(latest):
            return latest, False
        if latest.status == "succeeded":
            return latest, False

    snapshot = analytics_snapshot_repository.create(db, repository_id=repository.id)
    await db.commit()
    return snapshot, True


async def run_generation(snapshot_id: uuid.UUID) -> None:
    """Entry point for the `generate_analytics_snapshot` arq task. Opens
    its own session — a worker task runs after the enqueueing request's
    session has already closed (same pattern as every other background
    task in this codebase)."""
    settings = get_settings()
    async with async_session_factory() as db:
        snapshot = await analytics_snapshot_repository.get(db, snapshot_id)
        if snapshot is None:
            logger.warning("AnalyticsSnapshot %s no longer exists; skipping", snapshot_id)
            return

        try:
            await _run_generation_body(db, snapshot, settings=settings)
        except Exception as exc:  # noqa: BLE001 — must always reach a terminal state
            logger.exception("Analytics snapshot generation %s failed", snapshot_id)
            analytics_snapshot_repository.mark_failed(
                snapshot, finished_at=datetime.now(UTC), error=str(exc)
            )
            await db.commit()
            await _publish_failure(db, snapshot)


async def _publish_failure(db: AsyncSession, snapshot: AnalyticsSnapshot) -> None:
    """Best-effort — see pr_analysis_service._publish_failure."""
    try:
        repository = await db.get(Repository, snapshot.repository_id)
        if repository is None:
            return
        await publish_state(
            category=EventCategory.AI_GENERATION,
            organization_id=repository.organization_id,
            repository_id=repository.id,
            resource="analytics_snapshot",
            data=AnalyticsSnapshotPublic.from_snapshot(snapshot).model_dump(mode="json"),
        )
        await publish_notification(
            organization_id=repository.organization_id,
            repository_id=repository.id,
            title=f"Analytics generation failed for {repository.full_name}",
            level="error",
        )
    except Exception:  # noqa: BLE001 — see docstring
        logger.exception("Failed to publish analytics failure event for %s", snapshot.id)


async def _fetch_hotspot_commit_files(
    token: str, full_name: str, shas: list[str]
) -> list[list[GitHubPullRequestFile]]:
    """Bounded concurrency, not one-at-a-time — a sequential fetch of up
    to MAX_HOTSPOT_COMMITS single-commit calls would make this background
    job needlessly slow."""
    semaphore = asyncio.Semaphore(_HOTSPOT_FETCH_CONCURRENCY)

    async def fetch(sha: str) -> list[GitHubPullRequestFile]:
        async with semaphore:
            return await rest_client.get_commit_files(token, full_name, sha=sha)

    return await asyncio.gather(*(fetch(sha) for sha in shas))


async def _run_generation_body(
    db: AsyncSession, snapshot: AnalyticsSnapshot, *, settings: Settings
) -> None:
    repository = await db.get(
        Repository, snapshot.repository_id, options=[selectinload(Repository.installation)]
    )
    if repository is None:
        raise RuntimeError(f"Repository {snapshot.repository_id} no longer exists")

    analytics_snapshot_repository.mark_running(snapshot, started_at=datetime.now(UTC))
    await db.commit()
    await publish_state(
        category=EventCategory.AI_GENERATION,
        organization_id=repository.organization_id,
        repository_id=repository.id,
        resource="analytics_snapshot",
        data=AnalyticsSnapshotPublic.from_snapshot(snapshot).model_dump(mode="json"),
    )

    installation = await github_installation_repository.get_by_id(db, repository.installation_id)
    if installation is None:
        raise RuntimeError(f"Installation {repository.installation_id} no longer exists")
    token = await app_client.get_installation_access_token(installation.github_installation_id)

    commits = await rest_client.list_commits_paginated(
        token, repository.full_name, branch=repository.default_branch
    )
    daily_commit_activity = commits_analytics.bucket_daily_commits(commits)

    hotspot_sample = commits[: rest_client.MAX_HOTSPOT_COMMITS]
    commit_files = await _fetch_hotspot_commit_files(
        token, repository.full_name, [c.sha for c in hotspot_sample]
    )
    dependents = await rank_files_by_dependents(db, repository.id, limit=10_000)
    dependents_by_path = {ranking.path: ranking.dependents_count for ranking in dependents}
    file_hotspots, architecture_hotspots = hotspots_analytics.aggregate_hotspots(
        commit_files, dependents_by_path=dependents_by_path, limit=settings.analytics_top_hotspots
    )

    pull_requests = await pull_request_repository.list_for_repository(db, repository.id, limit=200)
    issues = await issue_repository.list_for_repository(db, repository.id, limit=200)

    pr_daily = pr_analytics.bucket_daily_pr_counts(pull_requests)
    issue_daily = issues_analytics.bucket_daily_issue_counts(issues)
    daily_pr_issue_activity = [
        DailyPRIssueRecord(
            date=date,
            prs_opened=pr_daily.get(date, {}).get("opened", 0),
            prs_merged=pr_daily.get(date, {}).get("merged", 0),
            prs_closed=pr_daily.get(date, {}).get("closed", 0),
            issues_opened=issue_daily.get(date, 0),
        )
        for date in sorted(set(pr_daily) | set(issue_daily))
    ]

    contributor_activity = contributors_analytics.build_contributor_activity(
        daily_commit_activity, pull_requests
    )
    median_cycle_time_hours, pr_cycle_time_samples = pr_analytics.compute_cycle_time(
        pull_requests, limit=_MAX_CYCLE_TIME_SAMPLES
    )
    open_issues_total, stale_issues = issues_analytics.summarize_open_issues(
        issues,
        now=datetime.now(UTC),
        stale_after_days=settings.analytics_stale_issue_days,
        limit=_MAX_STALE_ISSUES,
    )

    analytics_snapshot_repository.mark_succeeded(
        snapshot,
        finished_at=datetime.now(UTC),
        synced_through=repository.last_synced_at,
        daily_commit_activity=daily_commit_activity,
        daily_pr_issue_activity=daily_pr_issue_activity,
        contributor_activity=contributor_activity,
        median_cycle_time_hours=median_cycle_time_hours,
        pr_cycle_time_samples=pr_cycle_time_samples,
        open_issues_total=open_issues_total,
        stale_issues=stale_issues,
        file_hotspots=file_hotspots,
        architecture_hotspots=architecture_hotspots,
        commit_sample_size=len(commits),
        hotspot_commit_sample_size=len(hotspot_sample),
        pr_sample_size=len(pull_requests),
    )
    await db.commit()
    await publish_state(
        category=EventCategory.AI_GENERATION,
        organization_id=repository.organization_id,
        repository_id=repository.id,
        resource="analytics_snapshot",
        data=AnalyticsSnapshotPublic.from_snapshot(snapshot).model_dump(mode="json"),
    )
    await publish_notification(
        organization_id=repository.organization_id,
        repository_id=repository.id,
        title=f"Analytics ready for {repository.full_name}",
        level="success",
    )
