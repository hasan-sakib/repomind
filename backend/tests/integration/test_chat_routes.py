import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from app.ai.embedding_provider import EmbeddingProvider, EmbeddingResult
from app.ai.factory import get_ai_provider, get_embedding_provider, get_reranker
from app.ai.provider import AIProvider, ChatMessage, CompletionResult
from app.ai.reranker import RerankedDocument, Reranker
from app.main import app
from tests.integration.test_repository_connect import (
    FAKE_REPO_JSON,
    _connect_installation,
    _mock_github_app_endpoints,
    _register_and_get_org_id,
)

pytestmark = pytest.mark.asyncio


class _FakeEmbeddingProvider(EmbeddingProvider):
    async def embed(self, texts: list[str], *, input_type: str) -> EmbeddingResult:
        return EmbeddingResult(
            vectors=[[0.1] * 1024 for _ in texts], model="fake-embed", total_tokens=1
        )


class _FakeReranker(Reranker):
    async def rerank(
        self, query: str, documents: list[str], *, top_k: int
    ) -> list[RerankedDocument]:
        return [
            RerankedDocument(index=i, relevance_score=1.0)
            for i in range(min(top_k, len(documents)))
        ]


class _FakeChatProvider(AIProvider):
    @property
    def model(self) -> str:
        return "fake-chat-model"

    async def complete(
        self, messages: list[ChatMessage], *, system: str | None = None, max_tokens: int = 4096
    ) -> CompletionResult:
        return CompletionResult(content="hi", input_tokens=1, output_tokens=1, model=self.model)

    async def stream(
        self, messages: list[ChatMessage], *, system: str | None = None, max_tokens: int = 4096
    ):
        yield "Hello "
        yield "world."


@pytest.fixture(autouse=True)
def _fake_ai_dependencies():
    app.dependency_overrides[get_ai_provider] = lambda: _FakeChatProvider()
    app.dependency_overrides[get_embedding_provider] = lambda: _FakeEmbeddingProvider()
    app.dependency_overrides[get_reranker] = lambda: _FakeReranker()
    yield
    # Popped, not `del` — the `client` fixture's own teardown
    # (`app.dependency_overrides.clear()`) may already have run first,
    # since fixture teardown order across independent autouse fixtures
    # isn't guaranteed relative to each other.
    app.dependency_overrides.pop(get_ai_provider, None)
    app.dependency_overrides.pop(get_embedding_provider, None)
    app.dependency_overrides.pop(get_reranker, None)


async def _connect_a_repository(client: AsyncClient, httpx_mock: HTTPXMock) -> str:
    org_id = await _register_and_get_org_id(client, "chat-owner@example.com")
    _mock_github_app_endpoints(httpx_mock)
    await _connect_installation(client, org_id)
    installations = (
        await client.get(f"/api/v1/organizations/{org_id}/github/installations")
    ).json()
    installation_id = installations[0]["id"]
    connect_response = await client.post(
        f"/api/v1/organizations/{org_id}/repositories",
        json={
            "installation_id": installation_id,
            "github_repo_id": FAKE_REPO_JSON["id"],
            "full_name": FAKE_REPO_JSON["full_name"],
        },
    )
    assert connect_response.status_code == 201, connect_response.text
    return str(connect_response.json()["id"])


async def test_ask_streams_sse_events_over_http(client: AsyncClient, httpx_mock: HTTPXMock) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)

    create_response = await client.post(f"/api/v1/repositories/{repository_id}/conversations")
    assert create_response.status_code == 201, create_response.text
    conversation_id = create_response.json()["id"]

    async with client.stream(
        "POST",
        f"/api/v1/repositories/{repository_id}/conversations/{conversation_id}/messages",
        json={"query": "Explain the authentication flow."},
    ) as response:
        assert response.status_code == 200
        body = ""
        async for chunk in response.aiter_text():
            body += chunk

    assert "event: sources" in body
    assert "event: token" in body
    assert "event: done" in body
    assert "Hello " in body and "world." in body

    detail_response = await client.get(
        f"/api/v1/repositories/{repository_id}/conversations/{conversation_id}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][1]["role"] == "assistant"
    assert detail["messages"][1]["content"] == "Hello world."
    assert detail["conversation"]["title"] is not None


async def test_ask_requires_csrf_header(client: AsyncClient, httpx_mock: HTTPXMock) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    create_response = await client.post(f"/api/v1/repositories/{repository_id}/conversations")
    conversation_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/repositories/{repository_id}/conversations/{conversation_id}/messages",
        json={"query": "Explain the authentication flow."},
        headers={"X-Requested-With": ""},
    )
    assert response.status_code == 403


async def test_set_feedback_over_http(client: AsyncClient, httpx_mock: HTTPXMock) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    create_response = await client.post(f"/api/v1/repositories/{repository_id}/conversations")
    conversation_id = create_response.json()["id"]

    async with client.stream(
        "POST",
        f"/api/v1/repositories/{repository_id}/conversations/{conversation_id}/messages",
        json={"query": "Where is payment processing implemented?"},
    ) as response:
        async for _ in response.aiter_text():
            pass

    detail = (
        await client.get(f"/api/v1/repositories/{repository_id}/conversations/{conversation_id}")
    ).json()
    assistant_message_id = detail["messages"][1]["id"]

    feedback_response = await client.patch(
        f"/api/v1/repositories/{repository_id}/conversations/{conversation_id}"
        f"/messages/{assistant_message_id}/feedback",
        json={"feedback": "up"},
    )
    assert feedback_response.status_code == 200, feedback_response.text
    assert feedback_response.json()["feedback"] == "up"
