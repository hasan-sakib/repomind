import re
import uuid

import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from app.db.session import async_session_factory
from app.repositories import repository_repository
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


async def _connect_a_repository(client: AsyncClient, httpx_mock: HTTPXMock) -> str:
    org_id = await _register_and_get_org_id(client, "analytics-routes@example.com")
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


def _mock_generation_endpoints(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=PAGINATED_COMMITS_URL, json=[_COMMIT_A])
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


async def test_get_snapshot_before_any_trigger_is_404(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)

    response = await client.get(f"/api/v1/repositories/{repository_id}/analytics")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "analytics_snapshot_not_found"


async def test_trigger_snapshot_before_syncing_is_409(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    async with async_session_factory() as db:
        repository = await repository_repository.get_by_id(db, uuid.UUID(repository_id))
        repository.last_synced_at = None
        await db.commit()

    response = await client.post(f"/api/v1/repositories/{repository_id}/analytics")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "repository_not_synced"


async def test_trigger_snapshot_runs_end_to_end_via_the_fake_arq_pool(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    _mock_generation_endpoints(httpx_mock)
    repository_id = await _connect_a_repository(client, httpx_mock)

    trigger_response = await client.post(f"/api/v1/repositories/{repository_id}/analytics")
    assert trigger_response.status_code == 202, trigger_response.text

    get_response = await client.get(f"/api/v1/repositories/{repository_id}/analytics")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["status"] == "succeeded"
    assert body["commit_sample_size"] == 1
    assert body["file_hotspots"][0]["path"] == "app/services/auth_service.py"


async def test_trigger_snapshot_twice_without_force_does_not_re_enqueue(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    _mock_generation_endpoints(httpx_mock)
    repository_id = await _connect_a_repository(client, httpx_mock)

    first = await client.post(f"/api/v1/repositories/{repository_id}/analytics")
    second = await client.post(f"/api/v1/repositories/{repository_id}/analytics")

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]


async def test_non_member_gets_404_on_analytics_snapshot(
    client: AsyncClient, second_client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _register_and_get_org_id(second_client, "analytics-outsider@example.com")

    response = await second_client.get(f"/api/v1/repositories/{repository_id}/analytics")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "repository_not_found"
