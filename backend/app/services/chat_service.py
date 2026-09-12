"""Orchestrates one chat turn: persist the question, run retrieval
(app/retrieval/graph.py), persist sources, stream the LLM's answer, persist
the answer. Every step commits as it completes — same "genuine progress,
not one write at the end" discipline as the indexing pipeline
(app/indexing/pipeline.py) — so a client that disconnects mid-stream still
finds its question and retrieved sources saved, not lost.

The actual retrieval+generation work (`_run_turn`) runs in a task spawned
by `_stream_turn`, deliberately decoupled from the HTTP request: a local
model (Ollama) can take tens of seconds to answer, long enough that a
closed tab, a navigation, or a flaky connection is a real, not
hypothetical, occurrence mid-stream. If that work ran inline in the
request's own async generator, the client disconnecting would let
Starlette close the generator — which, since it's paused inside an
`async for` over `ai_provider.stream()`, does not run `_run_turn`'s own
`except`/`mark_failed` handling, leaving the AiRun stuck at `running`
forever with no assistant message ever recorded. `_stream_turn` spawns
the work as an independent task against its *own* database session
(the request's session is torn down by FastAPI once the request ends,
mid-stream or not) and relays events to whichever client is still
listening through a queue; if nobody is, the task still runs to
completion and the database still ends up in a consistent final state.
"""

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Coroutine
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedding_provider import EmbeddingProvider
from app.ai.provider import AIProvider, ChatMessage
from app.ai.reranker import Reranker
from app.core.config import Settings
from app.db.session import async_session_factory
from app.models.ai_run import AiRun
from app.models.chat_status import MessageFeedback, MessageRole
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.repository import Repository
from app.repositories import (
    ai_run_repository,
    commit_repository,
    conversation_repository,
    message_repository,
    retrieval_result_repository,
)
from app.retrieval.graph import build_graph
from app.retrieval.prompt import SYSTEM_PROMPT, build_context_block, build_user_message
from app.retrieval.types import RetrievedChunk
from app.schemas.chat import (
    ChatStreamEvent,
    DoneEvent,
    ErrorEvent,
    MessagePublic,
    SourceReferencePublic,
    SourcesEvent,
    TokenEvent,
)
from app.services.exceptions import (
    ConversationNotFoundError,
    MessageNotFoundError,
    RegenerateNotAllowedError,
)

logger = logging.getLogger("repomind.chat")

# len(text) // 4 — the same rough token-count heuristic used for chunk
# sizing (app/indexing/chunker.py). AIProvider.stream() yields raw text
# with no usage totals attached, so this is an approximation for
# observability (AiRun.input_tokens/output_tokens), not a billing figure.
_CHARS_PER_TOKEN = 4

# asyncio only holds a *weak* reference to a task once created — without
# keeping our own strong reference somewhere, a spawned turn can be
# garbage-collected mid-run the moment nothing else (e.g. a disconnected
# client's now-closed generator) is holding it. This set is that
# reference; `task.add_done_callback` drops it again once the turn ends.
_background_turns: set[asyncio.Task[None]] = set()


def _spawn(coro: Coroutine[Any, Any, None]) -> asyncio.Task[None]:
    task = asyncio.create_task(coro)
    _background_turns.add(task)
    task.add_done_callback(_background_turns.discard)
    return task


def _make_title(query: str) -> str:
    single_line = " ".join(query.split())
    return single_line if len(single_line) <= 80 else single_line[:77] + "…"


async def start_conversation(
    db: AsyncSession, *, repository_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation:
    conversation = conversation_repository.create(
        db, repository_id=repository_id, created_by_user_id=user_id
    )
    await db.commit()
    return conversation


async def list_conversations(db: AsyncSession, repository_id: uuid.UUID) -> list[Conversation]:
    return await conversation_repository.list_for_repository(db, repository_id)


async def get_conversation_or_raise(
    db: AsyncSession, *, repository_id: uuid.UUID, conversation_id: uuid.UUID
) -> Conversation:
    conversation = await conversation_repository.get(db, conversation_id)
    # Same "not found" whether the conversation doesn't exist or belongs
    # to a different repository — see indexing_service.get_job_or_raise
    # for the same pattern and why.
    if conversation is None or conversation.repository_id != repository_id:
        raise ConversationNotFoundError("Conversation not found")
    return conversation


async def get_message_or_raise(
    db: AsyncSession, *, conversation_id: uuid.UUID, message_id: uuid.UUID
) -> Message:
    message = await message_repository.get(db, message_id)
    if message is None or message.conversation_id != conversation_id:
        raise MessageNotFoundError("Message not found")
    return message


async def get_user_message_or_raise(
    db: AsyncSession, *, conversation_id: uuid.UUID, message_id: uuid.UUID
) -> Message:
    message = await message_repository.get(db, message_id)
    if message is None or message.conversation_id != conversation_id:
        raise MessageNotFoundError("Message not found")
    if message.role != MessageRole.USER:
        raise RegenerateNotAllowedError("Only a user message can be regenerated from")
    return message


async def set_feedback(
    db: AsyncSession, *, message: Message, feedback: MessageFeedback | None
) -> None:
    message_repository.set_feedback(message, feedback)
    await db.commit()


async def get_conversation_messages(
    db: AsyncSession, *, conversation: Conversation, repository_id: uuid.UUID
) -> list[MessagePublic]:
    messages = await message_repository.list_for_conversation(db, conversation.id)
    assistant_ids = [m.id for m in messages if m.role == MessageRole.ASSISTANT]
    runs = await ai_run_repository.list_for_assistant_messages(db, assistant_ids)
    runs_by_message_id = {run.assistant_message_id: run for run in runs}

    commit_shas = {r.commit_sha for run in runs for r in run.retrieval_results if r.commit_sha}
    urls = await commit_repository.get_urls_by_shas(
        db, repository_id=repository_id, shas=commit_shas
    )

    result: list[MessagePublic] = []
    for message in messages:
        run = runs_by_message_id.get(message.id)
        if run is None:
            result.append(MessagePublic.from_message(message))
            continue
        sources = [
            SourceReferencePublic.from_result(r, commit_url=urls.get(r.commit_sha or ""))
            for r in sorted(run.retrieval_results, key=lambda r: r.rank)
        ]
        result.append(MessagePublic.from_message(message, intent=run.intent, sources=sources))
    return result


async def resolve_sources(
    db: AsyncSession, *, repository_id: uuid.UUID, run: AiRun
) -> list[SourceReferencePublic]:
    commit_shas = {r.commit_sha for r in run.retrieval_results if r.commit_sha}
    urls = await commit_repository.get_urls_by_shas(
        db, repository_id=repository_id, shas=commit_shas
    )
    return [
        SourceReferencePublic.from_result(r, commit_url=urls.get(r.commit_sha or ""))
        for r in sorted(run.retrieval_results, key=lambda r: r.rank)
    ]


async def ask(
    db: AsyncSession,
    *,
    conversation: Conversation,
    repository: Repository,
    query: str,
    ai_provider: AIProvider,
    embedding_provider: EmbeddingProvider,
    reranker: Reranker,
    settings: Settings,
) -> AsyncIterator[ChatStreamEvent]:
    user_message = message_repository.create(
        db, conversation_id=conversation.id, role=MessageRole.USER, content=query
    )
    if conversation.title is None:
        conversation_repository.set_title(conversation, _make_title(query))
    await db.flush()
    run = ai_run_repository.create(
        db, conversation_id=conversation.id, user_message_id=user_message.id
    )
    await db.commit()

    async for event in _stream_turn(
        repository_id=repository.id,
        conversation_id=conversation.id,
        run_id=run.id,
        query=query,
        ai_provider=ai_provider,
        embedding_provider=embedding_provider,
        reranker=reranker,
        settings=settings,
    ):
        yield event


async def regenerate(
    db: AsyncSession,
    *,
    conversation: Conversation,
    repository: Repository,
    user_message: Message,
    ai_provider: AIProvider,
    embedding_provider: EmbeddingProvider,
    reranker: Reranker,
    settings: Settings,
) -> AsyncIterator[ChatStreamEvent]:
    run = ai_run_repository.create(
        db, conversation_id=conversation.id, user_message_id=user_message.id
    )
    await db.commit()

    async for event in _stream_turn(
        repository_id=repository.id,
        conversation_id=conversation.id,
        run_id=run.id,
        query=user_message.content,
        ai_provider=ai_provider,
        embedding_provider=embedding_provider,
        reranker=reranker,
        settings=settings,
    ):
        yield event


async def _stream_turn(
    *,
    repository_id: uuid.UUID,
    conversation_id: uuid.UUID,
    run_id: uuid.UUID,
    query: str,
    ai_provider: AIProvider,
    embedding_provider: EmbeddingProvider,
    reranker: Reranker,
    settings: Settings,
) -> AsyncIterator[ChatStreamEvent]:
    """Spawns `_run_turn` as an independent task (its own DB session, not
    the caller's) and relays its events to whoever is still listening.
    If the caller stops listening — this generator gets closed because
    the HTTP client disconnected — the spawned task is deliberately left
    running: see the module docstring for why."""
    queue: asyncio.Queue[ChatStreamEvent | None] = asyncio.Queue()

    async def worker() -> None:
        try:
            async with async_session_factory() as worker_db:
                async for event in _run_turn(
                    worker_db,
                    repository_id=repository_id,
                    conversation_id=conversation_id,
                    run_id=run_id,
                    query=query,
                    ai_provider=ai_provider,
                    embedding_provider=embedding_provider,
                    reranker=reranker,
                    settings=settings,
                ):
                    await queue.put(event)
        finally:
            await queue.put(None)

    _spawn(worker())

    while True:
        event = await queue.get()
        if event is None:
            return
        yield event


async def _run_turn(
    db: AsyncSession,
    *,
    repository_id: uuid.UUID,
    conversation_id: uuid.UUID,
    run_id: uuid.UUID,
    query: str,
    ai_provider: AIProvider,
    embedding_provider: EmbeddingProvider,
    reranker: Reranker,
    settings: Settings,
) -> AsyncIterator[ChatStreamEvent]:
    run = await ai_run_repository.get(db, run_id)
    if run is None:
        # Only possible if the conversation was deleted in the moment
        # between this task being spawned and it actually starting.
        logger.warning("AiRun %s no longer exists; abandoning turn", run_id)
        return

    try:
        graph = build_graph(db, embedding_provider, reranker, settings)
        result = await graph.ainvoke({"repository_id": repository_id, "query": query})
        ranked: list[RetrievedChunk] = result.get("ranked", [])

        ai_run_repository.set_intent(run, result["intent"])
        for rank, chunk in enumerate(ranked, start=1):
            retrieval_result_repository.create(
                db,
                ai_run_id=run.id,
                source_type=chunk.source_type,
                rank=rank,
                score=chunk.score,
                chunk_id=chunk.chunk_id,
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                symbol_name=chunk.symbol_name,
                commit_sha=chunk.commit_sha,
            )
        await db.commit()
        await db.refresh(run, attribute_names=["retrieval_results"])

        sources = await resolve_sources(db, repository_id=repository_id, run=run)
        yield SourcesEvent(sources=sources)
    except Exception as exc:  # noqa: BLE001 — must surface as a stream event, not crash the worker
        logger.exception("Retrieval failed for ai_run %s", run.id)
        ai_run_repository.mark_failed(run, error=str(exc), finished_at=datetime.now(UTC))
        await db.commit()
        yield ErrorEvent(message="Something went wrong finding relevant context.")
        return

    context_block = build_context_block(ranked, max_chars=settings.rag_max_context_chars)
    messages = [ChatMessage(role="user", content=build_user_message(query, context_block))]

    response_text = ""
    try:
        async for token in ai_provider.stream(messages, system=SYSTEM_PROMPT):
            response_text += token
            yield TokenEvent(text=token)
    except Exception as exc:  # noqa: BLE001 — must surface as a stream event, not crash the worker
        logger.exception("Generation failed for ai_run %s", run.id)
        ai_run_repository.mark_failed(run, error=str(exc), finished_at=datetime.now(UTC))
        await db.commit()
        yield ErrorEvent(message="Something went wrong generating a response.")
        return

    assistant_message = message_repository.create(
        db, conversation_id=conversation_id, role=MessageRole.ASSISTANT, content=response_text
    )
    await db.flush()
    now = datetime.now(UTC)
    ai_run_repository.mark_succeeded(
        run,
        assistant_message_id=assistant_message.id,
        model=ai_provider.model,
        input_tokens=max(1, len(SYSTEM_PROMPT + context_block + query) // _CHARS_PER_TOKEN),
        output_tokens=max(1, len(response_text) // _CHARS_PER_TOKEN),
        latency_ms=int((now - run.created_at).total_seconds() * 1000),
        finished_at=now,
    )
    conversation = await conversation_repository.get(db, conversation_id)
    if conversation is not None:
        conversation_repository.touch(conversation, at=now)
    await db.commit()

    yield DoneEvent(message_id=assistant_message.id, run_id=run.id)
