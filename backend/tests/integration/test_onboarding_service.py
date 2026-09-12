import re
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from app.ai.provider import AIProvider, ChatMessage, CompletionResult
from app.db.session import async_session_factory
from app.models.indexing_status import IndexingJobStatus, IndexingTrigger
from app.models.onboarding_status import OnboardingGuideStatus
from app.repositories import (
    indexing_job_repository,
    onboarding_guide_repository,
    repository_repository,
)
from app.services import onboarding_service
from app.services.exceptions import RepositoryNotIndexedError
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


class FakeGuideProvider(AIProvider):
    def __init__(self, content: str) -> None:
        self._content = content

    @property
    def model(self) -> str:
        return "fake-onboarding-model"

    async def complete(
        self, messages: list[ChatMessage], *, system: str | None = None, max_tokens: int = 4096
    ) -> CompletionResult:
        return CompletionResult(
            content=self._content, input_tokens=15, output_tokens=25, model=self.model
        )

    async def stream(
        self, messages: list[ChatMessage], *, system: str | None = None, max_tokens: int = 4096
    ):
        yield self._content  # pragma: no cover — onboarding never streams


async def _connect_a_repository(client: AsyncClient, httpx_mock: HTTPXMock) -> str:
    org_id = await _register_and_get_org_id(client, "onboarding@example.com")
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


async def test_trigger_guide_generation_requires_a_successful_index(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)

    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        with pytest.raises(RepositoryNotIndexedError):
            await onboarding_service.trigger_guide_generation(db, repository=repository)


async def test_trigger_guide_generation_creates_a_queued_row(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _mark_indexed(repository_id)

    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        guide, started = await onboarding_service.trigger_guide_generation(
            db, repository=repository
        )

    assert started is True
    assert guide.status == OnboardingGuideStatus.QUEUED
    assert guide.commit_sha == "a" * 40


async def test_trigger_guide_generation_returns_cached_result_at_the_same_commit(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _mark_indexed(repository_id, commit_sha="b" * 40)

    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        guide = onboarding_guide_repository.create(
            db, repository_id=repository.id, commit_sha="b" * 40
        )
        onboarding_guide_repository.mark_succeeded(
            guide,
            finished_at=datetime.now(UTC),
            architecture_overview="x",
            common_workflows="y",
            authentication_flow=None,
            faq=[],
            important_modules=[],
            recommended_files=[],
            key_dependencies=[],
            dev_setup_steps=[],
            database_structure=[],
            learning_path=[],
            model="test-model",
            input_tokens=1,
            output_tokens=1,
        )
        await db.commit()
        cached_id = guide.id

        second, started = await onboarding_service.trigger_guide_generation(
            db, repository=repository
        )

    assert started is False
    assert second.id == cached_id


async def test_trigger_guide_generation_regenerates_after_a_new_successful_index(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _mark_indexed(repository_id, commit_sha="c" * 40)

    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        stale = onboarding_guide_repository.create(
            db, repository_id=repository.id, commit_sha="c" * 40
        )
        onboarding_guide_repository.mark_succeeded(
            stale,
            finished_at=datetime.now(UTC),
            architecture_overview="stale",
            common_workflows="stale",
            authentication_flow=None,
            faq=[],
            important_modules=[],
            recommended_files=[],
            key_dependencies=[],
            dev_setup_steps=[],
            database_structure=[],
            learning_path=[],
            model="test-model",
            input_tokens=1,
            output_tokens=1,
        )
        await db.commit()
        stale_id = stale.id

    await _mark_indexed(repository_id, commit_sha="d" * 40)

    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        fresh, started = await onboarding_service.trigger_guide_generation(
            db, repository=repository
        )

    assert started is True
    assert fresh.id != stale_id
    assert fresh.commit_sha == "d" * 40


async def test_run_generation_end_to_end_succeeds(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _mark_indexed(repository_id)
    httpx_mock.add_response(
        url=CONTENTS_URL,
        status_code=404,
        json={"message": "Not Found"},
        is_reusable=True,
        is_optional=True,
    )

    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        guide, started = await onboarding_service.trigger_guide_generation(
            db, repository=repository
        )
        assert started is True
        guide_id = guide.id

    await onboarding_service.run_generation(
        guide_id, ai_provider=FakeGuideProvider(VALID_GUIDE_JSON)
    )

    async with async_session_factory() as db:
        result = await onboarding_guide_repository.get(db, guide_id)

    assert result.status == OnboardingGuideStatus.SUCCEEDED
    assert result.architecture_overview == "This repository follows a layered structure."
    assert result.authentication_flow is None
    assert result.model == "fake-onboarding-model"
    assert result.input_tokens == 15


async def test_run_generation_marks_failed_on_invalid_llm_output(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _mark_indexed(repository_id)
    httpx_mock.add_response(
        url=CONTENTS_URL,
        status_code=404,
        json={"message": "Not Found"},
        is_reusable=True,
        is_optional=True,
    )

    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        guide, _ = await onboarding_service.trigger_guide_generation(db, repository=repository)
        guide_id = guide.id

    await onboarding_service.run_generation(guide_id, ai_provider=FakeGuideProvider("not json"))

    async with async_session_factory() as db:
        result = await onboarding_guide_repository.get(db, guide_id)

    assert result.status == OnboardingGuideStatus.FAILED
    assert result.error is not None


async def test_run_generation_skips_silently_if_the_row_no_longer_exists() -> None:
    await onboarding_service.run_generation(
        uuid.uuid4(), ai_provider=FakeGuideProvider(VALID_GUIDE_JSON)
    )


async def test_progress_round_trip(client: AsyncClient, httpx_mock: HTTPXMock) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)

    async with async_session_factory() as db:
        me = await client.get("/api/v1/auth/me")
        user_id = uuid.UUID(me.json()["user"]["id"])

        assert (
            await onboarding_service.get_progress(
                db, repository_id=uuid.UUID(repository_id), user_id=user_id
            )
            == set()
        )

        await onboarding_service.set_progress(
            db,
            repository_id=uuid.UUID(repository_id),
            user_id=user_id,
            item_key="section:architecture",
            completed=True,
        )
        assert await onboarding_service.get_progress(
            db, repository_id=uuid.UUID(repository_id), user_id=user_id
        ) == {"section:architecture"}

        # Marking the same item complete twice is a no-op, not an error.
        await onboarding_service.set_progress(
            db,
            repository_id=uuid.UUID(repository_id),
            user_id=user_id,
            item_key="section:architecture",
            completed=True,
        )
        assert await onboarding_service.get_progress(
            db, repository_id=uuid.UUID(repository_id), user_id=user_id
        ) == {"section:architecture"}

        await onboarding_service.set_progress(
            db,
            repository_id=uuid.UUID(repository_id),
            user_id=user_id,
            item_key="section:architecture",
            completed=False,
        )
        assert (
            await onboarding_service.get_progress(
                db, repository_id=uuid.UUID(repository_id), user_id=user_id
            )
            == set()
        )
