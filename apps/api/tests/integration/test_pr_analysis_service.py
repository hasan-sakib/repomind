import re
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from app.ai.provider import AIProvider, ChatMessage, CompletionResult
from app.db.session import async_session_factory
from app.domain.pr_analysis_status import PRAnalysisStatus
from app.repositories import pull_request_analysis_repository, pull_request_repository
from app.services import pr_analysis_service
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
  "affected_components": [
    {"name": "Authentication", "file_paths": ["app/services/auth_service.py"]}
  ],
  "potential_concerns": [
    {
      "description": "Refresh token logic changed",
      "file_path": "app/services/auth_service.py",
      "symbol_name": "AuthService"
    }
  ],
  "recommended_tests": [
    {"description": "Refresh token flow", "existing_test_file": null}
  ]
}"""


class FakeAnalysisProvider(AIProvider):
    def __init__(self, content: str) -> None:
        self._content = content

    @property
    def model(self) -> str:
        return "fake-analysis-model"

    async def complete(
        self, messages: list[ChatMessage], *, system: str | None = None, max_tokens: int = 4096
    ) -> CompletionResult:
        return CompletionResult(
            content=self._content, input_tokens=10, output_tokens=20, model=self.model
        )

    async def stream(
        self, messages: list[ChatMessage], *, system: str | None = None, max_tokens: int = 4096
    ):
        yield self._content  # pragma: no cover — analysis never streams


async def _connect_a_repository(client: AsyncClient, httpx_mock: HTTPXMock) -> str:
    org_id = await _register_and_get_org_id(client, "pr-analysis@example.com")
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


async def _seed_pull_request(repository_id: str, *, head_sha: str = "a" * 40) -> str:
    async with async_session_factory() as db:
        pr = pull_request_repository.create(
            db,
            repository_id=uuid.UUID(repository_id),
            number=183,
            title="Add refresh token rotation",
            state="open",
            author_login="dev",
            html_url="https://github.com/acme/widgets/pull/183",
            head_sha=head_sha,
            github_created_at=datetime.now(UTC),
            github_updated_at=datetime.now(UTC),
            closed_at=None,
            merged_at=None,
            synced_at=datetime.now(UTC),
        )
        await db.commit()
        return str(pr.id)


async def test_trigger_analysis_creates_a_queued_row(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _seed_pull_request(repository_id)

    async with async_session_factory() as db:
        pr = await pull_request_repository.get(
            db, repository_id=uuid.UUID(repository_id), number=183
        )
        analysis, started = await pr_analysis_service.trigger_analysis(db, pull_request=pr)

    assert started is True
    assert analysis.status == PRAnalysisStatus.QUEUED
    assert analysis.head_sha == "a" * 40


async def test_trigger_analysis_returns_cached_result_at_the_same_head_sha(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _seed_pull_request(repository_id, head_sha="b" * 40)

    async with async_session_factory() as db:
        pr = await pull_request_repository.get(
            db, repository_id=uuid.UUID(repository_id), number=183
        )
        analysis = pull_request_analysis_repository.create(
            db, pull_request_id=pr.id, head_sha="b" * 40
        )
        pull_request_analysis_repository.mark_succeeded(
            analysis,
            finished_at=datetime.now(UTC),
            risk_level="low",  # type: ignore[arg-type]
            summary="ok",
            affected_components=[],
            potential_concerns=[],
            recommended_tests=[],
            files_analyzed=[],
            model="test-model",
            input_tokens=1,
            output_tokens=1,
        )
        await db.commit()
        cached_id = analysis.id

        second, started = await pr_analysis_service.trigger_analysis(db, pull_request=pr)

    assert started is False
    assert second.id == cached_id


async def test_trigger_analysis_regenerates_after_a_new_commit_moves_head_sha(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _seed_pull_request(repository_id, head_sha="c" * 40)

    async with async_session_factory() as db:
        pr = await pull_request_repository.get(
            db, repository_id=uuid.UUID(repository_id), number=183
        )
        stale = pull_request_analysis_repository.create(
            db, pull_request_id=pr.id, head_sha="c" * 40
        )
        pull_request_analysis_repository.mark_succeeded(
            stale,
            finished_at=datetime.now(UTC),
            risk_level="low",  # type: ignore[arg-type]
            summary="stale",
            affected_components=[],
            potential_concerns=[],
            recommended_tests=[],
            files_analyzed=[],
            model="test-model",
            input_tokens=1,
            output_tokens=1,
        )
        await db.commit()
        stale_id = stale.id

        # A new commit was pushed — the PR's head_sha has since moved.
        pr.head_sha = "d" * 40
        await db.commit()

        fresh, started = await pr_analysis_service.trigger_analysis(db, pull_request=pr)

    assert started is True
    assert fresh.id != stale_id
    assert fresh.head_sha == "d" * 40


async def test_run_analysis_end_to_end_succeeds_and_validates_citations(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _seed_pull_request(repository_id)
    httpx_mock.add_response(
        url=PULL_REQUEST_FILES_URL,
        json=[
            {
                "filename": "app/services/auth_service.py",
                "status": "modified",
                "additions": 10,
                "deletions": 2,
                "changes": 12,
                "patch": "@@ -1,1 +1,2 @@\n+    pass",
            }
        ],
    )

    async with async_session_factory() as db:
        pr = await pull_request_repository.get(
            db, repository_id=uuid.UUID(repository_id), number=183
        )
        analysis, started = await pr_analysis_service.trigger_analysis(db, pull_request=pr)
        assert started is True
        analysis_id = analysis.id

    await pr_analysis_service.run_analysis(
        analysis_id, ai_provider=FakeAnalysisProvider(VALID_ANALYSIS_JSON)
    )

    async with async_session_factory() as db:
        result = await pull_request_analysis_repository.get(db, analysis_id)

    assert result.status == PRAnalysisStatus.SUCCEEDED
    assert result.risk_level == "high"
    assert result.model == "fake-analysis-model"
    assert result.input_tokens == 10
    assert result.output_tokens == 20
    assert result.affected_components[0]["file_paths"] == ["app/services/auth_service.py"]
    assert len(result.files_analyzed) == 1
    assert result.files_analyzed[0]["path"] == "app/services/auth_service.py"


async def test_run_analysis_marks_failed_on_invalid_llm_output(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _seed_pull_request(repository_id)
    httpx_mock.add_response(url=PULL_REQUEST_FILES_URL, json=[])

    async with async_session_factory() as db:
        pr = await pull_request_repository.get(
            db, repository_id=uuid.UUID(repository_id), number=183
        )
        analysis, _ = await pr_analysis_service.trigger_analysis(db, pull_request=pr)
        analysis_id = analysis.id

    # Every retry attempt returns garbage — the analysis must still reach
    # a terminal FAILED state rather than being left RUNNING forever.
    await pr_analysis_service.run_analysis(
        analysis_id, ai_provider=FakeAnalysisProvider("not json")
    )

    async with async_session_factory() as db:
        result = await pull_request_analysis_repository.get(db, analysis_id)

    assert result.status == PRAnalysisStatus.FAILED
    assert result.error is not None


async def test_run_analysis_skips_silently_if_the_row_no_longer_exists() -> None:
    # No exception should escape — this mirrors index_repository's guard
    # for a job whose row was deleted before the worker got to it.
    await pr_analysis_service.run_analysis(
        uuid.uuid4(), ai_provider=FakeAnalysisProvider(VALID_ANALYSIS_JSON)
    )
