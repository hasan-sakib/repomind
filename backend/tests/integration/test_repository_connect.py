import re

import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

pytestmark = pytest.mark.asyncio

TOKEN_URL = re.compile(r"^https://api\.github\.com/app/installations/\d+/access_tokens.*")
ACCOUNT_URL = re.compile(r"^https://api\.github\.com/app/installations/\d+$")
LIST_REPOS_URL = re.compile(r"^https://api\.github\.com/installation/repositories.*")
REPO_URL = re.compile(r"^https://api\.github\.com/repos/acme/widgets$")
BRANCHES_URL = re.compile(r"^https://api\.github\.com/repos/acme/widgets/branches.*")
COMMITS_URL = re.compile(r"^https://api\.github\.com/repos/acme/widgets/commits.*")
PULLS_URL = re.compile(r"^https://api\.github\.com/repos/acme/widgets/pulls.*")
ISSUES_URL = re.compile(r"^https://api\.github\.com/repos/acme/widgets/issues.*")

FAKE_REPO_JSON = {
    "id": 555,
    "full_name": "acme/widgets",
    "name": "widgets",
    "description": "Widget factory",
    "language": "Python",
    "stargazers_count": 12,
    "forks_count": 3,
    "default_branch": "main",
    "private": False,
    "html_url": "https://github.com/acme/widgets",
}


async def _register_and_get_org_id(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery", "full_name": "Test User"},
    )
    assert response.status_code == 201, response.text
    me = await client.get("/api/v1/auth/me")
    return str(me.json()["organizations"][0]["organization"]["id"])


def _mock_github_app_endpoints(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=ACCOUNT_URL,
        json={"account": {"login": "acme", "type": "Organization"}},
        is_reusable=True,
    )
    # Only ACCOUNT_URL is hit by every test (the install callback always
    # calls get_installation_account) — the rest depend on how far a given
    # test's flow actually gets, so they're optional rather than requiring
    # every test to exercise the full connect+sync pipeline.
    httpx_mock.add_response(
        url=TOKEN_URL,
        status_code=201,
        json={"token": "fake-installation-token"},
        is_reusable=True,
        is_optional=True,
    )
    httpx_mock.add_response(
        url=LIST_REPOS_URL,
        json={"repositories": [FAKE_REPO_JSON]},
        is_reusable=True,
        is_optional=True,
    )
    httpx_mock.add_response(url=REPO_URL, json=FAKE_REPO_JSON, is_reusable=True, is_optional=True)
    httpx_mock.add_response(url=BRANCHES_URL, json=[], is_reusable=True, is_optional=True)
    httpx_mock.add_response(url=COMMITS_URL, json=[], is_reusable=True, is_optional=True)
    httpx_mock.add_response(url=PULLS_URL, json=[], is_reusable=True, is_optional=True)
    httpx_mock.add_response(url=ISSUES_URL, json=[], is_reusable=True, is_optional=True)


async def _connect_installation(
    client: AsyncClient, organization_id: str, *, installation_id: int = 999
) -> None:
    install_response = await client.get(f"/api/v1/organizations/{organization_id}/github/install")
    assert install_response.status_code in (302, 307)
    state = client.cookies.get("rm_github_install_state")
    assert state is not None
    _, _, state_token = state.partition(":")

    callback_response = await client.get(
        "/api/v1/github/callback",
        params={"installation_id": str(installation_id), "state": state_token},
    )
    assert callback_response.status_code in (302, 307)


async def test_full_connect_and_sync_flow(client: AsyncClient, httpx_mock: HTTPXMock) -> None:
    org_id = await _register_and_get_org_id(client, "connect@example.com")
    _mock_github_app_endpoints(httpx_mock)

    await _connect_installation(client, org_id)

    installations_response = await client.get(
        f"/api/v1/organizations/{org_id}/github/installations"
    )
    assert installations_response.status_code == 200
    installations = installations_response.json()
    assert len(installations) == 1
    installation_id = installations[0]["id"]

    available_response = await client.get(
        f"/api/v1/organizations/{org_id}/github/installations/{installation_id}/available-repositories"
    )
    assert available_response.status_code == 200
    available = available_response.json()
    assert len(available) == 1
    assert available[0]["full_name"] == "acme/widgets"

    connect_response = await client.post(
        f"/api/v1/organizations/{org_id}/repositories",
        json={
            "installation_id": installation_id,
            "github_repo_id": 555,
            "full_name": "acme/widgets",
        },
    )
    assert connect_response.status_code == 201, connect_response.text
    repository_id = connect_response.json()["id"]

    # The background sync ran synchronously within the request/response
    # cycle under ASGITransport, so it's already complete here.
    overview_response = await client.get(f"/api/v1/repositories/{repository_id}")
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["repository"]["status"] == "ready"
    assert overview["repository"]["description"] == "Widget factory"
    assert overview["repository"]["stargazers_count"] == 12

    # Connecting the same repo again is rejected, not silently duplicated.
    duplicate_response = await client.post(
        f"/api/v1/organizations/{org_id}/repositories",
        json={
            "installation_id": installation_id,
            "github_repo_id": 555,
            "full_name": "acme/widgets",
        },
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"]["code"] == "repository_already_connected"

    # It no longer shows up as "available to connect".
    available_after = await client.get(
        f"/api/v1/organizations/{org_id}/github/installations/{installation_id}/available-repositories"
    )
    assert available_after.json() == []


async def test_non_admin_cannot_connect_repository(
    client: AsyncClient, second_client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    org_id = await _register_and_get_org_id(client, "owner-connect@example.com")
    _mock_github_app_endpoints(httpx_mock)
    await _connect_installation(client, org_id)

    viewer_response = await second_client.post(
        "/api/v1/auth/register",
        json={
            "email": "viewer-connect@example.com",
            "password": "correct-horse-battery",
            "full_name": "Viewer",
        },
    )
    assert viewer_response.status_code == 201
    viewer_id = viewer_response.json()["user"]["id"]

    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "viewer-connect@example.com", "role": "viewer"},
    )

    installations = (
        await client.get(f"/api/v1/organizations/{org_id}/github/installations")
    ).json()
    installation_id = installations[0]["id"]

    response = await second_client.post(
        f"/api/v1/organizations/{org_id}/repositories",
        json={
            "installation_id": installation_id,
            "github_repo_id": 555,
            "full_name": "acme/widgets",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_role"
    assert viewer_id  # sanity: the viewer really was created and is distinct from the owner


async def test_non_member_gets_404_on_repository(
    client: AsyncClient, second_client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    org_id = await _register_and_get_org_id(client, "owner-repo@example.com")
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
            "github_repo_id": 555,
            "full_name": "acme/widgets",
        },
    )
    repository_id = connect_response.json()["id"]

    await _register_and_get_org_id(second_client, "outsider-repo@example.com")
    response = await second_client.get(f"/api/v1/repositories/{repository_id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "repository_not_found"
