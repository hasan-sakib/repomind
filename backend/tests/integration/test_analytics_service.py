import re
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from app.db.session import async_session_factory
from app.domain.analytics_status import AnalyticsSnapshotStatus
from app.repositories import analytics_snapshot_repository, repository_repository
from app.services import analytics_service
from app.services.exceptions import RepositoryNotSyncedError
from tests.integration.test_repository_connect import (
    FAKE_REPO_JSON,
    _connect_installation,
    _mock_github_app_endpoints,
    _register_and_get_org_id,
)

pytestmark = pytest.mark.asyncio

PAGINATED_COMMITS_URL = re.compile(
    r"^https://api\.github\.com/repos/acme/widgets/commits\?.*page=1.*"
)
COMMIT_DETAIL_URL = re.compile(r"^https://api\.github\.com/repos/acme/widgets/commits/[a-f0-9]+$")

_COMMIT_A = {
    "sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "html_url": "https://github.com/acme/widgets/commit/a",
    "commit": {"message": "Add feature", "author": {"name": "Ada", "date": "2026-01-01T00:00:00Z"}},
    "author": {"login": "ada"},
}
_COMMIT_B = {
    "sha": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "html_url": "https://github.com/acme/widgets/commit/b",
    "commit": {"message": "Fix bug", "author": {"name": "Ada", "date": "2026-01-02T00:00:00Z"}},
    "author": {"login": "ada"},
}


async def _connect_a_repository(client: AsyncClient, httpx_mock: HTTPXMock) -> str:
    org_id = await _register_and_get_org_id(client, "analytics@example.com")
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


async def _mark_synced(repository_id: str) -> None:
    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        repository_repository.mark_synced(repository, at=datetime.now(UTC))
        await db.commit()


def _mock_generation_endpoints(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=PAGINATED_COMMITS_URL, json=[_COMMIT_A, _COMMIT_B])
    httpx_mock.add_response(
        url=COMMIT_DETAIL_URL,
        json={
            "sha": "x",
            "files": [
                {
                    "filename": "app/services/auth_service.py",
                    "status": "modified",
                    "additions": 3,
                    "deletions": 1,
                    "changes": 4,
                }
            ],
        },
        is_reusable=True,
    )


async def test_trigger_snapshot_generation_requires_a_sync(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)

    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        repository.last_synced_at = None
        await db.commit()

        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        with pytest.raises(RepositoryNotSyncedError):
            await analytics_service.trigger_snapshot_generation(db, repository=repository)


async def test_trigger_snapshot_generation_creates_a_queued_row(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)

    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        snapshot, started = await analytics_service.trigger_snapshot_generation(
            db, repository=repository
        )

    assert started is True
    assert snapshot.status == AnalyticsSnapshotStatus.QUEUED


async def test_trigger_snapshot_generation_returns_cached_result_without_force(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)

    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        cached = analytics_snapshot_repository.create(db, repository_id=repository.id)
        analytics_snapshot_repository.mark_succeeded(
            cached,
            finished_at=datetime.now(UTC),
            synced_through=repository.last_synced_at,
            daily_commit_activity=[],
            daily_pr_issue_activity=[],
            contributor_activity=[],
            median_cycle_time_hours=None,
            pr_cycle_time_samples=[],
            open_issues_total=0,
            stale_issues=[],
            file_hotspots=[],
            architecture_hotspots=[],
            commit_sample_size=0,
            hotspot_commit_sample_size=0,
            pr_sample_size=0,
        )
        await db.commit()
        cached_id = cached.id

        second, started = await analytics_service.trigger_snapshot_generation(
            db, repository=repository
        )

    assert started is False
    assert second.id == cached_id


async def test_trigger_snapshot_generation_with_force_always_regenerates(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)

    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        cached = analytics_snapshot_repository.create(db, repository_id=repository.id)
        analytics_snapshot_repository.mark_succeeded(
            cached,
            finished_at=datetime.now(UTC),
            synced_through=repository.last_synced_at,
            daily_commit_activity=[],
            daily_pr_issue_activity=[],
            contributor_activity=[],
            median_cycle_time_hours=None,
            pr_cycle_time_samples=[],
            open_issues_total=0,
            stale_issues=[],
            file_hotspots=[],
            architecture_hotspots=[],
            commit_sample_size=0,
            hotspot_commit_sample_size=0,
            pr_sample_size=0,
        )
        await db.commit()
        cached_id = cached.id

        fresh, started = await analytics_service.trigger_snapshot_generation(
            db, repository=repository, force=True
        )

    assert started is True
    assert fresh.id != cached_id


async def test_run_generation_end_to_end_succeeds(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    _mock_generation_endpoints(httpx_mock)

    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        snapshot, started = await analytics_service.trigger_snapshot_generation(
            db, repository=repository
        )
        assert started is True
        snapshot_id = snapshot.id

    await analytics_service.run_generation(snapshot_id)

    async with async_session_factory() as db:
        result = await analytics_snapshot_repository.get(db, snapshot_id)

    assert result.status == AnalyticsSnapshotStatus.SUCCEEDED
    assert result.commit_sample_size == 2
    assert result.hotspot_commit_sample_size == 2
    assert len(result.daily_commit_activity) == 2
    assert result.file_hotspots[0]["path"] == "app/services/auth_service.py"
    assert result.file_hotspots[0]["change_count"] == 2


async def test_run_generation_marks_failed_on_unexpected_error(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    httpx_mock.add_response(url=PAGINATED_COMMITS_URL, status_code=500, text="boom")

    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        snapshot, _ = await analytics_service.trigger_snapshot_generation(db, repository=repository)
        snapshot_id = snapshot.id

    await analytics_service.run_generation(snapshot_id)

    async with async_session_factory() as db:
        result = await analytics_snapshot_repository.get(db, snapshot_id)

    assert result.status == AnalyticsSnapshotStatus.FAILED
    assert result.error is not None


async def test_run_generation_skips_silently_if_the_row_no_longer_exists() -> None:
    await analytics_service.run_generation(uuid.uuid4())
