import re
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from app.ai.provider import AIProvider, ChatMessage, CompletionResult
from app.db.session import async_session_factory
from app.models.indexing_status import IndexingJobStatus, IndexingTrigger
from app.repositories import indexing_job_repository
from app.workers import tasks as worker_tasks
from tests.integration.test_repository_connect import (
    FAKE_REPO_JSON,
    _connect_installation,
    _mock_github_app_endpoints,
    _register_and_get_org_id,
)

pytestmark = pytest.mark.asyncio

CONTENTS_URL = re.compile(r"^https://api\.github\.com/repos/acme/widgets/contents/.*")

VALID_GUIDE_JSON = """{
  "architecture_overview": "This repository follows a layered structure.",
  "common_workflows": "A request flows through the route layer into a service.",
  "authentication_flow": null,
  "faq": []
}"""


class _FakeProvider(AIProvider):
    @property
    def model(self) -> str:
        return "fake-model"

    async def complete(
        self, messages: list[ChatMessage], *, system: str | None = None, max_tokens: int = 4096
    ) -> CompletionResult:
        return CompletionResult(
            content=VALID_GUIDE_JSON, input_tokens=5, output_tokens=15, model=self.model
        )

    async def stream(
        self, messages: list[ChatMessage], *, system: str | None = None, max_tokens: int = 4096
    ):
        yield VALID_GUIDE_JSON  # pragma: no cover — onboarding never streams


async def _connect_a_repository(client: AsyncClient, httpx_mock: HTTPXMock) -> str:
    org_id = await _register_and_get_org_id(client, "onboarding-routes@example.com")
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


async def _mark_indexed(repository_id: str, *, commit_sha: str = "a" * 40) -> None:
    async with async_session_factory() as db:
        job = indexing_job_repository.create(
            db,
            repository_id=uuid.UUID(repository_id),
            trigger=IndexingTrigger.INITIAL,
            commit_sha=commit_sha,
        )
        await db.flush()
        indexing_job_repository.mark_finished(
            job, status=IndexingJobStatus.SUCCEEDED, finished_at=datetime.now(UTC), error=None
        )
        await db.commit()


async def test_get_guide_before_any_trigger_is_404(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)

    response = await client.get(f"/api/v1/repositories/{repository_id}/onboarding")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "onboarding_guide_not_found"


async def test_trigger_guide_before_indexing_is_409(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)

    response = await client.post(f"/api/v1/repositories/{repository_id}/onboarding")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "repository_not_indexed"


async def test_trigger_guide_runs_end_to_end_via_the_fake_arq_pool(
    client: AsyncClient, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(worker_tasks, "get_ai_provider", lambda: _FakeProvider())
    httpx_mock.add_response(
        url=CONTENTS_URL,
        status_code=404,
        json={"message": "Not Found"},
        is_reusable=True,
        is_optional=True,
    )

    repository_id = await _connect_a_repository(client, httpx_mock)
    await _mark_indexed(repository_id)

    trigger_response = await client.post(f"/api/v1/repositories/{repository_id}/onboarding")
    assert trigger_response.status_code == 202, trigger_response.text

    get_response = await client.get(f"/api/v1/repositories/{repository_id}/onboarding")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["status"] == "succeeded"
    assert body["architecture_overview"] == "This repository follows a layered structure."
    assert body["model"] == "fake-model"


async def test_trigger_guide_twice_without_force_does_not_re_enqueue(
    client: AsyncClient, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(worker_tasks, "get_ai_provider", lambda: _FakeProvider())
    httpx_mock.add_response(
        url=CONTENTS_URL,
        status_code=404,
        json={"message": "Not Found"},
        is_reusable=True,
        is_optional=True,
    )

    repository_id = await _connect_a_repository(client, httpx_mock)
    await _mark_indexed(repository_id)

    first = await client.post(f"/api/v1/repositories/{repository_id}/onboarding")
    second = await client.post(f"/api/v1/repositories/{repository_id}/onboarding")

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]


async def test_progress_round_trip_over_http(client: AsyncClient, httpx_mock: HTTPXMock) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)

    initial = await client.get(f"/api/v1/repositories/{repository_id}/onboarding/progress")
    assert initial.status_code == 200
    assert initial.json() == []

    set_response = await client.put(
        f"/api/v1/repositories/{repository_id}/onboarding/progress/section:architecture",
        json={"completed": True},
    )
    assert set_response.status_code == 204

    after_set = await client.get(f"/api/v1/repositories/{repository_id}/onboarding/progress")
    assert after_set.json() == ["section:architecture"]

    unset_response = await client.put(
        f"/api/v1/repositories/{repository_id}/onboarding/progress/section:architecture",
        json={"completed": False},
    )
    assert unset_response.status_code == 204

    after_unset = await client.get(f"/api/v1/repositories/{repository_id}/onboarding/progress")
    assert after_unset.json() == []


async def test_non_member_gets_404_on_onboarding_guide(
    client: AsyncClient, second_client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _register_and_get_org_id(second_client, "onboarding-outsider@example.com")

    response = await second_client.get(f"/api/v1/repositories/{repository_id}/onboarding")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "repository_not_found"
