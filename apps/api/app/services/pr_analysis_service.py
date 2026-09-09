"""Orchestrates one PR analysis: trigger (create-or-return-cached, mirrors
indexing_service.trigger_indexing), and the actual work run by the
`analyze_pull_request` arq task (app/workers/tasks.py) — gather context
(app/pr_analysis/context.py), call the LLM, validate its citations, and
persist a terminal state. Mirrors ADR 0005's chat_service.py in one
respect: any failure marks the row FAILED rather than leaving it stuck at
RUNNING forever — there's no HTTP client to "disconnect" here (this runs
entirely on the worker), but an unhandled exception in a worker task can
just as easily leave a row permanently unresolved if nothing catches it.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.provider import AIProvider, ChatMessage
from app.core.config import Settings, get_settings
from app.db.session import async_session_factory
from app.domain.pull_request import PullRequest
from app.domain.pull_request_analysis import (
    AffectedComponentRecord,
    ChangedFileRecord,
    PotentialConcernRecord,
    PullRequestAnalysis,
    RecommendedTestRecord,
)
from app.domain.repository import Repository
from app.integrations.github import app_client, rest_client
from app.pr_analysis import prompt as pr_prompt
from app.pr_analysis.context import PRAnalysisContext, build_context
from app.pr_analysis.result_schema import (
    PRAnalysisParseError,
    PRAnalysisResult,
    parse_llm_output,
    validate_citations,
)
from app.repositories import (
    github_installation_repository,
    pull_request_analysis_repository,
    pull_request_repository,
)
from app.services.exceptions import PullRequestAnalysisNotFoundError, PullRequestNotFoundError

logger = logging.getLogger("repomind.pr_analysis")

_MAX_PARSE_ATTEMPTS = 2  # one retry with a stricter reminder, then give up


async def get_pull_request_or_raise(
    db: AsyncSession, *, repository_id: uuid.UUID, number: int
) -> PullRequest:
    pr = await pull_request_repository.get(db, repository_id=repository_id, number=number)
    if pr is None:
        raise PullRequestNotFoundError("Pull request not found")
    return pr


async def get_latest_analysis_or_raise(
    db: AsyncSession, *, pull_request_id: uuid.UUID
) -> PullRequestAnalysis:
    analysis = await pull_request_analysis_repository.get_latest_for_pull_request(
        db, pull_request_id
    )
    if analysis is None:
        raise PullRequestAnalysisNotFoundError("This pull request hasn't been analyzed yet")
    return analysis


async def trigger_analysis(
    db: AsyncSession, *, pull_request: PullRequest, force: bool = False
) -> tuple[PullRequestAnalysis, bool]:
    """Returns (analysis, started). `started=False` means the caller
    already has what it needs — either a run is already in flight, or a
    succeeded analysis already exists at the PR's current head_sha, so
    there's nothing new to enqueue."""
    latest = await pull_request_analysis_repository.get_latest_for_pull_request(db, pull_request.id)
    if latest is not None and not force:
        if pull_request_analysis_repository.is_active(latest):
            return latest, False
        if latest.head_sha == pull_request.head_sha and latest.status == "succeeded":
            return latest, False

    analysis = pull_request_analysis_repository.create(
        db, pull_request_id=pull_request.id, head_sha=pull_request.head_sha
    )
    await db.commit()
    return analysis, True


async def run_analysis(analysis_id: uuid.UUID, *, ai_provider: AIProvider) -> None:
    """Entry point for the `analyze_pull_request` arq task. Opens its own
    session — a worker task runs after the enqueueing request's session
    has already closed (same pattern as sync_service.run_sync_in_background)."""
    settings = get_settings()
    async with async_session_factory() as db:
        analysis = await pull_request_analysis_repository.get(db, analysis_id)
        if analysis is None:
            logger.warning("PullRequestAnalysis %s no longer exists; skipping", analysis_id)
            return

        try:
            await _run_analysis_body(db, analysis, ai_provider=ai_provider, settings=settings)
        except Exception as exc:  # noqa: BLE001 — must always reach a terminal state
            logger.exception("PR analysis %s failed", analysis_id)
            pull_request_analysis_repository.mark_failed(
                analysis, finished_at=datetime.now(UTC), error=str(exc)
            )
            await db.commit()


async def _run_analysis_body(
    db: AsyncSession,
    analysis: PullRequestAnalysis,
    *,
    ai_provider: AIProvider,
    settings: Settings,
) -> None:
    pr = await db.get(PullRequest, analysis.pull_request_id)
    if pr is None:
        raise RuntimeError(f"PullRequest {analysis.pull_request_id} no longer exists")
    repository = await db.get(
        Repository, pr.repository_id, options=[selectinload(Repository.installation)]
    )
    if repository is None:
        raise RuntimeError(f"Repository {pr.repository_id} no longer exists")

    pull_request_analysis_repository.mark_running(analysis, started_at=datetime.now(UTC))
    await db.commit()

    installation = await github_installation_repository.get_by_id(db, repository.installation_id)
    if installation is None:
        raise RuntimeError(f"Installation {repository.installation_id} no longer exists")
    token = await app_client.get_installation_access_token(installation.github_installation_id)

    files = await rest_client.list_pull_request_files(token, repository.full_name, number=pr.number)
    context = await build_context(
        db,
        repository_id=repository.id,
        files=files,
        max_patch_chars=settings.pr_analysis_max_patch_chars_per_file,
    )
    result, input_tokens, output_tokens = await _complete_analysis(
        ai_provider,
        pr_number=pr.number,
        pr_title=pr.title,
        context=context,
        max_tokens=settings.pr_analysis_max_output_tokens,
    )
    validated = validate_citations(result, context.valid_file_paths())

    pull_request_analysis_repository.mark_succeeded(
        analysis,
        finished_at=datetime.now(UTC),
        risk_level=validated.risk_level,  # type: ignore[arg-type]
        summary=validated.summary,
        affected_components=[
            AffectedComponentRecord(name=c.name, file_paths=c.file_paths)
            for c in validated.affected_components
        ],
        potential_concerns=[
            PotentialConcernRecord(
                description=c.description, file_path=c.file_path, symbol_name=c.symbol_name
            )
            for c in validated.potential_concerns
        ],
        recommended_tests=[
            RecommendedTestRecord(
                description=t.description, existing_test_file=t.existing_test_file
            )
            for t in validated.recommended_tests
        ],
        files_analyzed=[
            ChangedFileRecord(
                path=f.filename, status=f.status, additions=f.additions, deletions=f.deletions
            )
            for f in files
        ],
        model=ai_provider.model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    await db.commit()


async def _complete_analysis(
    ai_provider: AIProvider,
    *,
    pr_number: int,
    pr_title: str,
    context: PRAnalysisContext,
    max_tokens: int,
) -> tuple[PRAnalysisResult, int, int]:
    user_message = pr_prompt.build_user_message(
        pr_number=pr_number, pr_title=pr_title, context=context
    )
    messages = [ChatMessage(role="user", content=user_message)]

    last_error: PRAnalysisParseError | None = None
    for _attempt in range(_MAX_PARSE_ATTEMPTS):
        completion = await ai_provider.complete(
            messages, system=pr_prompt.SYSTEM_PROMPT, max_tokens=max_tokens
        )
        try:
            result = parse_llm_output(completion.content)
            return result, completion.input_tokens, completion.output_tokens
        except PRAnalysisParseError as exc:
            last_error = exc
            messages.append(ChatMessage(role="assistant", content=completion.content))
            messages.append(
                ChatMessage(role="user", content=pr_prompt.build_retry_message(completion.content))
            )

    assert last_error is not None
    raise last_error
