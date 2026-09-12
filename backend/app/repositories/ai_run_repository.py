import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_run import AiRun
from app.models.chat_status import AiRunStatus, QueryIntent


async def get(db: AsyncSession, run_id: uuid.UUID) -> AiRun | None:
    result = await db.execute(
        select(AiRun).options(selectinload(AiRun.retrieval_results)).where(AiRun.id == run_id)
    )
    return result.scalar_one_or_none()


async def list_for_user_message(db: AsyncSession, user_message_id: uuid.UUID) -> list[AiRun]:
    """Every attempt at answering one user question — regenerating creates
    a new row here rather than overwriting the previous attempt."""
    result = await db.execute(
        select(AiRun).where(AiRun.user_message_id == user_message_id).order_by(AiRun.created_at)
    )
    return list(result.scalars().all())


async def list_for_assistant_messages(
    db: AsyncSession, assistant_message_ids: list[uuid.UUID]
) -> list[AiRun]:
    """The run that produced each assistant message — used to attach
    sources when rendering a conversation's full message history."""
    if not assistant_message_ids:
        return []
    result = await db.execute(
        select(AiRun)
        .options(selectinload(AiRun.retrieval_results))
        .where(AiRun.assistant_message_id.in_(assistant_message_ids))
    )
    return list(result.scalars().all())


def create(db: AsyncSession, *, conversation_id: uuid.UUID, user_message_id: uuid.UUID) -> AiRun:
    run = AiRun(
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        status=AiRunStatus.RUNNING,
    )
    db.add(run)
    return run


def set_intent(run: AiRun, intent: QueryIntent) -> None:
    run.intent = intent


def mark_succeeded(
    run: AiRun,
    *,
    assistant_message_id: uuid.UUID,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    finished_at: datetime,
) -> None:
    run.status = AiRunStatus.SUCCEEDED
    run.assistant_message_id = assistant_message_id
    run.model = model
    run.input_tokens = input_tokens
    run.output_tokens = output_tokens
    run.latency_ms = latency_ms
    run.finished_at = finished_at


def mark_failed(run: AiRun, *, error: str, finished_at: datetime) -> None:
    run.status = AiRunStatus.FAILED
    run.error = error
    run.finished_at = finished_at
