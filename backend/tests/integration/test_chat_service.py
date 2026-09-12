import asyncio
import hashlib
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedding_provider import EmbeddingProvider, EmbeddingResult
from app.ai.provider import AIProvider, ChatMessage, CompletionResult
from app.ai.reranker import RerankedDocument, Reranker
from app.core.config import get_settings
from app.db.session import async_session_factory
from app.domain.chat_status import AiRunStatus, MessageFeedback, MessageRole, QueryIntent
from app.repositories import (
    ai_run_repository,
    code_chunk_repository,
    code_embedding_repository,
    code_file_repository,
    github_installation_repository,
    message_repository,
    organization_repository,
    repository_repository,
    user_repository,
)
from app.schemas.chat import DoneEvent, ErrorEvent, SourcesEvent, TokenEvent
from app.services import chat_service

pytestmark = pytest.mark.asyncio


class FakeEmbeddingProvider(EmbeddingProvider):
    async def embed(self, texts: list[str], *, input_type: str) -> EmbeddingResult:
        return EmbeddingResult(
            vectors=[[0.1] * 1024 for _ in texts], model="fake-embed", total_tokens=1
        )


class FakeReranker(Reranker):
    async def rerank(
        self, query: str, documents: list[str], *, top_k: int
    ) -> list[RerankedDocument]:
        return [
            RerankedDocument(index=i, relevance_score=1.0 - i * 0.01)
            for i in range(min(top_k, len(documents)))
        ]


class FakeChatProvider(AIProvider):
    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens

    @property
    def model(self) -> str:
        return "fake-chat-model"

    async def complete(
        self, messages: list[ChatMessage], *, system: str | None = None, max_tokens: int = 4096
    ) -> CompletionResult:
        text = "".join(self._tokens)
        return CompletionResult(content=text, input_tokens=1, output_tokens=1, model=self.model)

    async def stream(
        self, messages: list[ChatMessage], *, system: str | None = None, max_tokens: int = 4096
    ):
        for token in self._tokens:
            yield token


class SlowFakeChatProvider(AIProvider):
    """Like FakeChatProvider, but paced — gives a test a real window to
    abandon the stream mid-generation, the way a disconnected client
    would with a genuinely slow model (e.g. Ollama)."""

    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens

    @property
    def model(self) -> str:
        return "slow-fake-chat-model"

    async def complete(
        self, messages: list[ChatMessage], *, system: str | None = None, max_tokens: int = 4096
    ) -> CompletionResult:
        text = "".join(self._tokens)
        return CompletionResult(content=text, input_tokens=1, output_tokens=1, model=self.model)

    async def stream(
        self, messages: list[ChatMessage], *, system: str | None = None, max_tokens: int = 4096
    ):
        for token in self._tokens:
            await asyncio.sleep(0.05)
            yield token


async def _seed_repository_with_chunk(db: AsyncSession) -> uuid.UUID:
    organization = organization_repository.create(
        db, name="Acme", slug=f"acme-{uuid.uuid4().hex[:8]}"
    )
    await db.flush()
    installation = github_installation_repository.create(
        db,
        organization_id=organization.id,
        github_installation_id=uuid.uuid4().int % 1_000_000_000,
        account_login="acme",
        account_type="Organization",
    )
    await db.flush()
    repository = repository_repository.create(
        db,
        organization_id=organization.id,
        installation_id=installation.id,
        github_repo_id=1,
        full_name="acme/widgets",
        name="widgets",
        description=None,
        language="Python",
        stargazers_count=0,
        forks_count=0,
        default_branch="main",
        private=False,
        html_url="https://github.com/acme/widgets",
    )
    await db.flush()

    code_file = code_file_repository.create(
        db,
        repository_id=repository.id,
        path="app/services/auth_service.py",
        language="python",
        size_bytes=200,
        content_hash="a" * 64,
        commit_sha="b" * 40,
        imports=[],
        indexed_at=datetime.now(UTC),
    )
    await db.flush()

    content = "def rotate_refresh_token(token):\n    return issue_new_token(token)"
    chunk = code_chunk_repository.create(
        db,
        file_id=code_file.id,
        symbol_id=None,
        chunk_type="function",
        content=content,
        start_line=10,
        end_line=11,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        token_count=20,
    )
    await db.flush()
    code_embedding_repository.create(
        db, chunk_id=chunk.id, embedding=[0.1] * 1024, model="fake-embed"
    )
    await db.commit()
    return repository.id


async def _create_user(db: AsyncSession) -> uuid.UUID:
    user = user_repository.create(
        db, email=f"{uuid.uuid4().hex[:8]}@example.com", full_name="Test User"
    )
    await db.commit()
    return user.id


async def test_ask_streams_sources_tokens_and_persists_conversation(
    db_session: AsyncSession,
) -> None:
    repository_id = await _seed_repository_with_chunk(db_session)
    repository = await repository_repository.get_by_id(db_session, repository_id)
    assert repository is not None
    conversation = await chat_service.start_conversation(
        db_session, repository_id=repository_id, user_id=await _create_user(db_session)
    )

    events = [
        event
        async for event in chat_service.ask(
            db_session,
            conversation=conversation,
            repository=repository,
            query="How does refresh token rotation work?",
            ai_provider=FakeChatProvider(
                ["Refresh tokens are rotated", " via rotate_refresh_token [1]."]
            ),
            embedding_provider=FakeEmbeddingProvider(),
            reranker=FakeReranker(),
            settings=get_settings(),
        )
    ]

    sources_events = [e for e in events if isinstance(e, SourcesEvent)]
    token_events = [e for e in events if isinstance(e, TokenEvent)]
    done_events = [e for e in events if isinstance(e, DoneEvent)]

    assert len(sources_events) == 1
    assert len(done_events) == 1
    assert not any(isinstance(e, ErrorEvent) for e in events)

    source = sources_events[0].sources[0]
    assert source.file_path == "app/services/auth_service.py"
    assert source.start_line == 10

    full_text = "".join(e.text for e in token_events)
    assert full_text == "Refresh tokens are rotated via rotate_refresh_token [1]."

    messages = await message_repository.list_for_conversation(db_session, conversation.id)
    assert [m.role for m in messages] == [MessageRole.USER, MessageRole.ASSISTANT]
    assert messages[1].content == full_text
    assert conversation.title is not None

    run = await ai_run_repository.get(db_session, done_events[0].run_id)
    assert run is not None
    assert run.status == AiRunStatus.SUCCEEDED
    assert run.intent == QueryIntent.EXPLAIN
    assert run.model == "fake-chat-model"
    assert len(run.retrieval_results) == 1


async def test_regenerate_creates_a_second_ai_run_for_the_same_question(
    db_session: AsyncSession,
) -> None:
    repository_id = await _seed_repository_with_chunk(db_session)
    repository = await repository_repository.get_by_id(db_session, repository_id)
    assert repository is not None
    conversation = await chat_service.start_conversation(
        db_session, repository_id=repository_id, user_id=await _create_user(db_session)
    )

    first_events = [
        event
        async for event in chat_service.ask(
            db_session,
            conversation=conversation,
            repository=repository,
            query="Where is payment processing implemented?",
            ai_provider=FakeChatProvider(["first answer"]),
            embedding_provider=FakeEmbeddingProvider(),
            reranker=FakeReranker(),
            settings=get_settings(),
        )
    ]
    first_done = next(e for e in first_events if isinstance(e, DoneEvent))

    messages = await message_repository.list_for_conversation(db_session, conversation.id)
    user_message = next(m for m in messages if m.role == MessageRole.USER)

    second_events = [
        event
        async for event in chat_service.regenerate(
            db_session,
            conversation=conversation,
            repository=repository,
            user_message=user_message,
            ai_provider=FakeChatProvider(["second answer"]),
            embedding_provider=FakeEmbeddingProvider(),
            reranker=FakeReranker(),
            settings=get_settings(),
        )
    ]
    second_done = next(e for e in second_events if isinstance(e, DoneEvent))

    runs = await ai_run_repository.list_for_user_message(db_session, user_message.id)
    assert len(runs) == 2
    assert {r.id for r in runs} == {first_done.run_id, second_done.run_id}

    all_messages = await message_repository.list_for_conversation(db_session, conversation.id)
    assistant_texts = {m.content for m in all_messages if m.role == MessageRole.ASSISTANT}
    assert assistant_texts == {"first answer", "second answer"}


async def test_ask_surfaces_error_event_and_marks_run_failed_when_ranking_fails(
    db_session: AsyncSession,
) -> None:
    repository_id = await _seed_repository_with_chunk(db_session)
    repository = await repository_repository.get_by_id(db_session, repository_id)
    assert repository is not None
    conversation = await chat_service.start_conversation(
        db_session, repository_id=repository_id, user_id=await _create_user(db_session)
    )

    # The reranker itself doesn't raise (ranking.rank() catches that and
    # falls back to source order) — this simulates a failure further
    # upstream by using an embedding provider that raises, since that's
    # what actually propagates out of the retrieval graph uncaught.
    class FailingEmbeddingProvider(EmbeddingProvider):
        async def embed(self, texts: list[str], *, input_type: str) -> EmbeddingResult:
            raise RuntimeError("embedding service unavailable")

    events = [
        event
        async for event in chat_service.ask(
            db_session,
            conversation=conversation,
            repository=repository,
            query="Explain the auth flow",
            ai_provider=FakeChatProvider(["unused"]),
            embedding_provider=FailingEmbeddingProvider(),
            reranker=FakeReranker(),
            settings=get_settings(),
        )
    ]

    assert any(isinstance(e, ErrorEvent) for e in events)
    assert not any(isinstance(e, DoneEvent) for e in events)

    messages = await message_repository.list_for_conversation(db_session, conversation.id)
    assert len(messages) == 1  # only the user message — no assistant message on failure

    runs = await ai_run_repository.list_for_user_message(db_session, messages[0].id)
    assert len(runs) == 1
    assert runs[0].status == AiRunStatus.FAILED


async def test_set_feedback_persists_on_message(db_session: AsyncSession) -> None:
    repository_id = await _seed_repository_with_chunk(db_session)
    repository = await repository_repository.get_by_id(db_session, repository_id)
    assert repository is not None
    conversation = await chat_service.start_conversation(
        db_session, repository_id=repository_id, user_id=await _create_user(db_session)
    )
    events = [
        event
        async for event in chat_service.ask(
            db_session,
            conversation=conversation,
            repository=repository,
            query="Explain the auth flow",
            ai_provider=FakeChatProvider(["answer"]),
            embedding_provider=FakeEmbeddingProvider(),
            reranker=FakeReranker(),
            settings=get_settings(),
        )
    ]
    done = next(e for e in events if isinstance(e, DoneEvent))
    message = await message_repository.get(db_session, done.message_id)
    assert message is not None

    await chat_service.set_feedback(db_session, message=message, feedback=MessageFeedback.UP)

    refreshed = await message_repository.get(db_session, done.message_id)
    assert refreshed is not None
    assert refreshed.feedback == MessageFeedback.UP


async def test_ask_completes_in_the_background_after_the_client_disconnects(
    db_session: AsyncSession,
) -> None:
    """Regression test: a client (browser tab closed, navigation, flaky
    connection) abandoning the SSE stream mid-generation must not leave
    the AiRun stuck at `running` forever with no assistant message ever
    recorded — see the module docstring on app/services/chat_service.py
    for why this is a real, not hypothetical, failure mode with a slow
    model. Simulates the abandonment by explicitly closing the async
    generator right after the first (sources) event, before any tokens
    have streamed, then waits for chat_service's own tracked background
    tasks to finish and checks the *final* state from a fresh session —
    mirroring what a client would see if it reconnected later."""
    repository_id = await _seed_repository_with_chunk(db_session)
    repository = await repository_repository.get_by_id(db_session, repository_id)
    assert repository is not None
    conversation = await chat_service.start_conversation(
        db_session, repository_id=repository_id, user_id=await _create_user(db_session)
    )

    stream = chat_service.ask(
        db_session,
        conversation=conversation,
        repository=repository,
        query="How does refresh token rotation work?",
        ai_provider=SlowFakeChatProvider(["Refresh ", "tokens ", "rotate."]),
        embedding_provider=FakeEmbeddingProvider(),
        reranker=FakeReranker(),
        settings=get_settings(),
    )
    first_event = await stream.__anext__()
    assert isinstance(first_event, SourcesEvent)
    await stream.aclose()  # simulates Starlette closing the generator on disconnect

    # The generation itself (SlowFakeChatProvider) hasn't finished yet —
    # give chat_service's spawned background task the time it needs to.
    await asyncio.wait_for(
        asyncio.gather(*chat_service._background_turns, return_exceptions=True), timeout=5
    )

    async with async_session_factory() as fresh_db:
        messages = await message_repository.list_for_conversation(fresh_db, conversation.id)
        assert [m.role for m in messages] == [MessageRole.USER, MessageRole.ASSISTANT]
        assert messages[1].content == "Refresh tokens rotate."

        runs = await ai_run_repository.list_for_user_message(fresh_db, messages[0].id)
        assert len(runs) == 1
        assert runs[0].status == AiRunStatus.SUCCEEDED
