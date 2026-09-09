"""arq task functions. There is a single indexing task, not one task per
trigger source (initial index / manual re-index / webhook-triggered
update) — the IndexingTrigger recorded on the job is data, and the
content-hash-based skip in app/indexing/pipeline.py already means a
"re-index" only reprocesses files that actually changed. Splitting that
into separate near-identical task functions would duplicate the same
pipeline call for no behavioral difference; see
docs/architecture/0004-codebase-indexing.md."""

import logging
import uuid
from typing import Any

from app.ai.factory import get_ai_provider, get_embedding_provider
from app.db.session import async_session_factory
from app.indexing.pipeline import run_indexing_job
from app.repositories import indexing_job_repository
from app.services import onboarding_service, pr_analysis_service, sync_service

logger = logging.getLogger("repomind.workers")


async def index_repository(ctx: dict[str, Any], job_id: str) -> None:
    """Runs an already-created IndexingJob (see
    app.services.indexing_service.trigger_indexing, which creates the row
    before enqueueing this task — the row is the source of truth for
    duplicate-prevention and for what to index, this task just executes it)."""
    async with async_session_factory() as db:
        job = await indexing_job_repository.get(db, uuid.UUID(job_id))
        if job is None:
            logger.warning("Indexing job %s no longer exists; skipping", job_id)
            return
        await run_indexing_job(db, job, get_embedding_provider())


async def sync_repository(ctx: dict[str, Any], repository_id: str) -> None:
    """GitHub metadata/branch/commit/PR/issue sync — moved onto arq from
    FastAPI BackgroundTasks now that a worker queue exists anyway for
    indexing; see docs/architecture/0003-github-integration.md and
    docs/architecture/0004-codebase-indexing.md."""
    await sync_service.run_sync_in_background(uuid.UUID(repository_id))


async def analyze_pull_request(ctx: dict[str, Any], analysis_id: str) -> None:
    """Runs an already-created PullRequestAnalysis (see
    app.services.pr_analysis_service.trigger_analysis, which creates the
    row before enqueueing this task). See
    docs/architecture/0007-ai-pull-request-intelligence.md."""
    await pr_analysis_service.run_analysis(uuid.UUID(analysis_id), ai_provider=get_ai_provider())


async def generate_onboarding_guide(ctx: dict[str, Any], guide_id: str) -> None:
    """Runs an already-created OnboardingGuide (see
    app.services.onboarding_service.trigger_guide_generation, which
    creates the row before enqueueing this task). See
    docs/architecture/0008-developer-onboarding.md."""
    await onboarding_service.run_generation(uuid.UUID(guide_id), ai_provider=get_ai_provider())
