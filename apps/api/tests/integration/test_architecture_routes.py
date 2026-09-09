import re
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from app.db.session import async_session_factory
from app.repositories import code_file_repository, code_symbol_repository
from tests.integration.test_repository_connect import (
    FAKE_REPO_JSON,
    _connect_installation,
    _mock_github_app_endpoints,
    _register_and_get_org_id,
)

_COMMITS_FOR_PATH_URL = re.compile(
    r"^https://api\.github\.com/repos/acme/widgets/commits\?.*path=.*"
)

pytestmark = pytest.mark.asyncio


async def _connect_a_repository(client: AsyncClient, httpx_mock: HTTPXMock) -> str:
    org_id = await _register_and_get_org_id(client, "arch-owner@example.com")
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


async def _seed_code(repository_id: str) -> str:
    """Seeds directly via a fresh session — mirrors how the real indexing
    pipeline writes this data, independent of the HTTP layer under test."""
    async with async_session_factory() as db:
        service_file = code_file_repository.create(
            db,
            repository_id=uuid.UUID(repository_id),
            path="app/services/auth_service.py",
            language="python",
            size_bytes=10,
            content_hash="a" * 64,
            commit_sha="f" * 40,
            imports=[],
            indexed_at=datetime.now(UTC),
        )
        await db.flush()
        code_symbol_repository.create(
            db,
            file_id=service_file.id,
            symbol_type="class",
            name="AuthService",
            start_line=1,
            end_line=20,
            signature="class AuthService:",
            docstring="Handles auth.",
            parent_symbol_id=None,
        )
        await db.commit()
        return str(service_file.id)


async def test_get_package_graph_over_http(client: AsyncClient, httpx_mock: HTTPXMock) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _seed_code(repository_id)

    response = await client.get(f"/api/v1/repositories/{repository_id}/architecture/graph")

    assert response.status_code == 200, response.text
    body = response.json()
    assert any(n["id"] == "package:app/services" for n in body["nodes"])


async def test_get_module_graph_over_http(client: AsyncClient, httpx_mock: HTTPXMock) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _seed_code(repository_id)

    response = await client.get(
        f"/api/v1/repositories/{repository_id}/architecture/graph",
        params={"package": "app/services"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["nodes"]) == 1
    assert body["nodes"][0]["label"] == "AuthService"


async def test_get_module_graph_for_unknown_package_is_404(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _seed_code(repository_id)

    response = await client.get(
        f"/api/v1/repositories/{repository_id}/architecture/graph",
        params={"package": "does/not/exist"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "architecture_package_not_found"


async def test_get_file_detail_over_http(client: AsyncClient, httpx_mock: HTTPXMock) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    file_id = await _seed_code(repository_id)

    response = await client.get(
        f"/api/v1/repositories/{repository_id}/architecture/files/{file_id}"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["path"] == "app/services/auth_service.py"
    assert body["symbols"][0]["name"] == "AuthService"


async def test_get_file_detail_for_unknown_file_is_404(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)

    response = await client.get(
        f"/api/v1/repositories/{repository_id}/architecture/files/"
        "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "architecture_file_not_found"


async def test_search_over_http(client: AsyncClient, httpx_mock: HTTPXMock) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _seed_code(repository_id)

    response = await client.get(
        f"/api/v1/repositories/{repository_id}/architecture/search", params={"q": "Auth"}
    )

    assert response.status_code == 200, response.text
    assert response.json()[0]["path"] == "app/services/auth_service.py"


async def test_get_recent_changes_over_http(client: AsyncClient, httpx_mock: HTTPXMock) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    file_id = await _seed_code(repository_id)

    httpx_mock.add_response(
        url=_COMMITS_FOR_PATH_URL,
        json=[
            {
                "sha": "abc123",
                "commit": {
                    "message": "Add login",
                    "author": {"name": "Dev", "date": "2026-01-01T00:00:00Z"},
                },
                "author": {"login": "dev"},
                "html_url": "https://github.com/acme/widgets/commit/abc123",
            }
        ],
    )

    response = await client.get(
        f"/api/v1/repositories/{repository_id}/architecture/files/{file_id}/recent-changes"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body[0]["sha"] == "abc123"
    assert body[0]["message"] == "Add login"


async def test_non_member_gets_404_on_architecture_graph(
    client: AsyncClient, second_client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _connect_a_repository(client, httpx_mock)
    await _register_and_get_org_id(second_client, "arch-outsider@example.com")

    response = await second_client.get(f"/api/v1/repositories/{repository_id}/architecture/graph")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "repository_not_found"
