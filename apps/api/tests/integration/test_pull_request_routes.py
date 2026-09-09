import re
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from app.ai.provider import AIProvider, ChatMessage, CompletionResult
from app.db.session import async_session_factory
from app.repositories import pull_request_repository
from app.workers import tasks as worker_tasks
from tests.integration.test_repository_connect import (
    FAKE_REPO_JSON,
    _connect_installation,
    _mock_github_app_endpoints,
    _register_and_get_org_id,
)

pytestmark = pytest.mark.asyncio

PULL_REQUEST_FILES_URL = re.compile(
    r"^https://api\.github\.com/repos/acme/widgets/pulls/183/files.*"
)

VALID_ANALYSIS_JSON = """{
  "summary": "Adds refresh-token rotation to the auth service.",
  "risk_level": "high",
  "affected_components": [],
  "potential_concerns": [],
  "recommended_tests": []
}"""


class _FakeProvider(AIProvider):
    @property
    def model(self) -> str:
        return "fake-model"

    async def complete(
        self, messages: list[ChatMessage], *, system: str | None = None, max_tokens: int = 4096
    ) -> CompletionResult:
        return CompletionResult(
            content=VALID_ANALYSIS_JSON, input_tokens=5, output_tokens=15, model=self.model
        )

    async def stream(
        self, messages: list[ChatMessage], *, system: str | None = None, max_tokens: int = 4096
    ):
        yield VALID_ANALYSIS_JSON  # pragma: no cover — analysis never streams


async def _connect_a_repository(client: AsyncClient, httpx_mock: HTTPXMock) -> str:
    org_id = await _register_and_get_org_id(client, "pr-routes@example.com")
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


async def _seed_pull_request(repository_id: str) -> None:
    async with async_session_factory() as db:
        pull_request_repository.create(
            db,
            repository_id=uuid.UUID(repository_id),
            number=183,
            title="Add refresh token rotation",
            state="open",
            author_login="dev",
            html_url="https://github.com/acme/widgets/pull/183",
            head_sha="a" * 40,
            github_created_at=datetime.now(UTC),
            github_updated_at=datetime.now(UTC),
            closed_at=None,
            merged_at=None,
            synced_at=datetime.now(UTC),
        )
        await db.commit()


async def test_get_pull_request_over_http(client: AsyncClient, httpx_mock: HTTPXMock) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _seed_pull_request(repository_id)

    response = await client.get(f"/api/v1/repositories/{repository_id}/pull-requests/183")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Add refresh token rotation"
    assert body["head_sha"] == "a" * 40


async def test_get_unknown_pull_request_is_404(client: AsyncClient, httpx_mock: HTTPXMock) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)

    response = await client.get(f"/api/v1/repositories/{repository_id}/pull-requests/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "pull_request_not_found"


async def test_get_analysis_before_any_trigger_is_404(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _seed_pull_request(repository_id)

    response = await client.get(f"/api/v1/repositories/{repository_id}/pull-requests/183/analysis")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "pull_request_analysis_not_found"


async def test_trigger_analysis_runs_end_to_end_via_the_fake_arq_pool(
    client: AsyncClient, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(worker_tasks, "get_ai_provider", lambda: _FakeProvider())

    repository_id = await _connect_a_repository(client, httpx_mock)
    await _seed_pull_request(repository_id)
    httpx_mock.add_response(url=PULL_REQUEST_FILES_URL, json=[])

    trigger_response = await client.post(
        f"/api/v1/repositories/{repository_id}/pull-requests/183/analysis"
    )
    assert trigger_response.status_code == 202, trigger_response.text

    # FakeArqPool (tests/conftest.py) runs the enqueued job inline, so by
    # the time the POST responds the analysis has already completed —
    # fetch it fresh to check the persisted state, not the response body
    # (which reflects the row as it was the instant it was created).
    get_response = await client.get(
        f"/api/v1/repositories/{repository_id}/pull-requests/183/analysis"
    )
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["status"] == "succeeded"
    assert body["risk_level"] == "high"
    assert body["model"] == "fake-model"


async def test_trigger_analysis_twice_without_force_does_not_re_enqueue(
    client: AsyncClient, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(worker_tasks, "get_ai_provider", lambda: _FakeProvider())

    repository_id = await _connect_a_repository(client, httpx_mock)
    await _seed_pull_request(repository_id)
    httpx_mock.add_response(url=PULL_REQUEST_FILES_URL, json=[])

    first = await client.post(f"/api/v1/repositories/{repository_id}/pull-requests/183/analysis")
    second = await client.post(f"/api/v1/repositories/{repository_id}/pull-requests/183/analysis")

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]


async def test_non_member_gets_404_on_pull_request(
    client: AsyncClient, second_client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _seed_pull_request(repository_id)
    await _register_and_get_org_id(second_client, "pr-outsider@example.com")

    response = await second_client.get(f"/api/v1/repositories/{repository_id}/pull-requests/183")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "repository_not_found"
