"""Orchestrates onboarding guide generation: trigger (create-or-return-
cached, mirrors pr_analysis_service.trigger_analysis / ADR 0007) and the
actual work run by the `generate_onboarding_guide` arq task
(app/workers/tasks.py) — gather context (app/onboarding/context.py), call
the LLM for the narrative sections, validate its citations, and persist a
terminal state. Also owns per-user onboarding progress tracking.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.provider import AIProvider, ChatMessage
from app.core.config import Settings, get_settings
from app.db.session import async_session_factory
from app.domain.onboarding_guide import (
    DatabaseStructureEntryRecord,
    DependencyRecord,
    FaqEntryRecord,
    ImportantModuleRecord,
    LearningPathStepRecord,
    OnboardingGuide,
    RecommendedFileRecord,
    SetupStepRecord,
)
from app.domain.repository import Repository
from app.events.publish import publish_notification, publish_state
from app.events.types import EventCategory
from app.integrations.github import app_client
from app.onboarding import prompt as onboarding_prompt
from app.onboarding.context import OnboardingContext, build_context
from app.onboarding.result_schema import (
    OnboardingGuideResult,
    OnboardingParseError,
    parse_llm_output,
    validate_citations,
)
from app.repositories import (
    github_installation_repository,
    indexing_job_repository,
    onboarding_guide_repository,
    onboarding_progress_repository,
)
from app.schemas.onboarding import OnboardingGuidePublic
from app.services.exceptions import OnboardingGuideNotFoundError, RepositoryNotIndexedError

logger = logging.getLogger("repomind.onboarding")

_MAX_PARSE_ATTEMPTS = 2  # one retry with a stricter reminder, then give up


async def get_latest_guide_or_raise(db: AsyncSession, repository_id: uuid.UUID) -> OnboardingGuide:
    guide = await onboarding_guide_repository.get_latest_for_repository(db, repository_id)
    if guide is None:
        raise OnboardingGuideNotFoundError("This repository hasn't been onboarded yet")
    return guide


async def trigger_guide_generation(
    db: AsyncSession, *, repository: Repository, force: bool = False
) -> tuple[OnboardingGuide, bool]:
    """Returns (guide, started). The cache key is the repository's latest
    *successful* index commit_sha (ADR 0004/0008) — a guide only goes
    stale once a new index actually finishes, not on every page view."""
    latest_index = await indexing_job_repository.get_latest_succeeded_for_repository(
        db, repository.id
    )
    if latest_index is None:
        raise RepositoryNotIndexedError(
            "Index this repository before generating an onboarding guide"
        )

    latest_guide = await onboarding_guide_repository.get_latest_for_repository(db, repository.id)
    if latest_guide is not None and not force:
        if onboarding_guide_repository.is_active(latest_guide):
            return latest_guide, False
        if (
            latest_guide.commit_sha == latest_index.commit_sha
            and latest_guide.status == "succeeded"
        ):
            return latest_guide, False

    guide = onboarding_guide_repository.create(
        db, repository_id=repository.id, commit_sha=latest_index.commit_sha
    )
    await db.commit()
    return guide, True


async def get_progress(
    db: AsyncSession, *, repository_id: uuid.UUID, user_id: uuid.UUID
) -> set[str]:
    return await onboarding_progress_repository.list_completed_item_keys(
        db, repository_id=repository_id, user_id=user_id
    )


async def set_progress(
    db: AsyncSession,
    *,
    repository_id: uuid.UUID,
    user_id: uuid.UUID,
    item_key: str,
    completed: bool,
) -> None:
    if completed:
        await onboarding_progress_repository.mark_completed(
            db, repository_id=repository_id, user_id=user_id, item_key=item_key
        )
    else:
        await onboarding_progress_repository.mark_incomplete(
            db, repository_id=repository_id, user_id=user_id, item_key=item_key
        )
    await db.commit()


async def run_generation(guide_id: uuid.UUID, *, ai_provider: AIProvider) -> None:
    """Entry point for the `generate_onboarding_guide` arq task. Opens its
    own session — a worker task runs after the enqueueing request's
    session has already closed (same pattern as
    sync_service.run_sync_in_background / pr_analysis_service.run_analysis)."""
    settings = get_settings()
    async with async_session_factory() as db:
        guide = await onboarding_guide_repository.get(db, guide_id)
        if guide is None:
            logger.warning("OnboardingGuide %s no longer exists; skipping", guide_id)
            return

        try:
            await _run_generation_body(db, guide, ai_provider=ai_provider, settings=settings)
        except Exception as exc:  # noqa: BLE001 — must always reach a terminal state
            logger.exception("Onboarding guide generation %s failed", guide_id)
            onboarding_guide_repository.mark_failed(
                guide, finished_at=datetime.now(UTC), error=str(exc)
            )
            await db.commit()
            await _publish_failure(db, guide)


async def _publish_failure(db: AsyncSession, guide: OnboardingGuide) -> None:
    """Best-effort — see pr_analysis_service._publish_failure."""
    try:
        repository = await db.get(Repository, guide.repository_id)
        if repository is None:
            return
        await publish_state(
            category=EventCategory.AI_GENERATION,
            organization_id=repository.organization_id,
            repository_id=repository.id,
            resource="onboarding_guide",
            data=OnboardingGuidePublic.from_guide(guide).model_dump(mode="json"),
        )
        await publish_notification(
            organization_id=repository.organization_id,
            repository_id=repository.id,
            title=f"Onboarding guide failed to generate for {repository.full_name}",
            level="error",
        )
    except Exception:  # noqa: BLE001 — see docstring
        logger.exception("Failed to publish onboarding failure event for %s", guide.id)


async def _run_generation_body(
    db: AsyncSession,
    guide: OnboardingGuide,
    *,
    ai_provider: AIProvider,
    settings: Settings,
) -> None:
    repository = await db.get(
        Repository, guide.repository_id, options=[selectinload(Repository.installation)]
    )
    if repository is None:
        raise RuntimeError(f"Repository {guide.repository_id} no longer exists")

    onboarding_guide_repository.mark_running(guide, started_at=datetime.now(UTC))
    await db.commit()
    await publish_state(
        category=EventCategory.AI_GENERATION,
        organization_id=repository.organization_id,
        repository_id=repository.id,
        resource="onboarding_guide",
        data=OnboardingGuidePublic.from_guide(guide).model_dump(mode="json"),
    )

    installation = await github_installation_repository.get_by_id(db, repository.installation_id)
    if installation is None:
        raise RuntimeError(f"Installation {repository.installation_id} no longer exists")
    token = await app_client.get_installation_access_token(installation.github_installation_id)

    context = await build_context(
        db,
        repository_id=repository.id,
        installation_token=token,
        full_name=repository.full_name,
        commit_sha=guide.commit_sha,
    )
    result, input_tokens, output_tokens = await _complete_guide(
        ai_provider,
        repository_full_name=repository.full_name,
        context=context,
        max_tokens=settings.onboarding_max_output_tokens,
    )
    validated = validate_citations(result, context.valid_file_paths())

    onboarding_guide_repository.mark_succeeded(
        guide,
        finished_at=datetime.now(UTC),
        architecture_overview=validated.architecture_overview,
        common_workflows=validated.common_workflows,
        authentication_flow=validated.authentication_flow,
        faq=[
            FaqEntryRecord(question=f.question, answer=f.answer, file_paths=f.file_paths)
            for f in validated.faq
        ],
        important_modules=[
            ImportantModuleRecord(name=m.name, path=m.path, kind=m.kind, file_count=m.file_count)
            for m in context.important_modules
        ],
        recommended_files=[
            RecommendedFileRecord(
                path=r.path, label=r.label, kind=r.kind, dependents_count=r.dependents_count
            )
            for r in context.recommended_files
        ],
        key_dependencies=[
            DependencyRecord(name=d.name, version=d.version, ecosystem=d.ecosystem)
            for d in context.key_dependencies
        ],
        dev_setup_steps=[
            SetupStepRecord(
                order=s.order,
                description=s.description,
                command=s.command,
                detected_from=s.detected_from,
            )
            for s in context.setup_steps
        ],
        database_structure=[
            DatabaseStructureEntryRecord(
                path=e.path, class_name=e.class_name, symbol_type=e.symbol_type
            )
            for e in context.database_structure
        ],
        learning_path=[
            LearningPathStepRecord(step=s.step, label=s.label, path=s.path, reason=s.reason)
            for s in context.learning_path
        ],
        model=ai_provider.model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    await db.commit()
    await publish_state(
        category=EventCategory.AI_GENERATION,
        organization_id=repository.organization_id,
        repository_id=repository.id,
        resource="onboarding_guide",
        data=OnboardingGuidePublic.from_guide(guide).model_dump(mode="json"),
    )
    await publish_notification(
        organization_id=repository.organization_id,
        repository_id=repository.id,
        title=f"Onboarding guide ready for {repository.full_name}",
        level="success",
    )


async def _complete_guide(
    ai_provider: AIProvider,
    *,
    repository_full_name: str,
    context: OnboardingContext,
    max_tokens: int,
) -> tuple[OnboardingGuideResult, int, int]:
    user_message = onboarding_prompt.build_user_message(
        repository_full_name=repository_full_name, context=context
    )
    messages = [ChatMessage(role="user", content=user_message)]

    last_error: OnboardingParseError | None = None
    for _attempt in range(_MAX_PARSE_ATTEMPTS):
        completion = await ai_provider.complete(
            messages, system=onboarding_prompt.SYSTEM_PROMPT, max_tokens=max_tokens
        )
        try:
            result = parse_llm_output(completion.content)
            return result, completion.input_tokens, completion.output_tokens
        except OnboardingParseError as exc:
            last_error = exc
            messages.append(ChatMessage(role="assistant", content=completion.content))
            messages.append(
                ChatMessage(
                    role="user", content=onboarding_prompt.build_retry_message(completion.content)
                )
            )

    assert last_error is not None
    raise last_error
