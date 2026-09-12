import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from tests.integration.test_repository_connect import (
    _connect_installation,
    _mock_github_app_endpoints,
    _register_and_get_org_id,
)

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, email: str, full_name: str = "Test User") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery", "full_name": full_name},
    )
    assert response.status_code == 201, response.text
    return response.json()["user"]


async def _connect_a_repository(client: AsyncClient, org_id: str, httpx_mock: HTTPXMock) -> str:
    _mock_github_app_endpoints(httpx_mock)
    await _connect_installation(client, org_id)
    installations = (
        await client.get(f"/api/v1/organizations/{org_id}/github/installations")
    ).json()
    connect_response = await client.post(
        f"/api/v1/organizations/{org_id}/repositories",
        json={
            "installation_id": installations[0]["id"],
            "github_repo_id": 555,
            "full_name": "acme/widgets",
        },
    )
    assert connect_response.status_code == 201, connect_response.text
    return str(connect_response.json()["id"])


async def test_new_member_is_auto_granted_access_and_admin_can_revoke_and_regrant_it(
    client: AsyncClient, second_client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    org_id = await _register_and_get_org_id(client, "permowner@example.com")
    member = await _register(second_client, "permmember@example.com")
    repository_id = await _connect_a_repository(client, org_id, httpx_mock)

    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "permmember@example.com", "role": "viewer"},
    )

    members = await client.get(f"/api/v1/repositories/{repository_id}/members")
    assert members.status_code == 200
    assert len(members.json()) == 2  # the owner, plus the auto-granted new member

    # The new member can see the repository, exactly per the auto-grant.
    assert (await second_client.get(f"/api/v1/repositories/{repository_id}")).status_code == 200

    revoke = await client.delete(f"/api/v1/repositories/{repository_id}/members/{member['id']}")
    assert revoke.status_code == 204

    after_revoke = await client.get(f"/api/v1/repositories/{repository_id}/members")
    assert len(after_revoke.json()) == 1

    # Revoked — the repository is now invisible to them.
    denied = await second_client.get(f"/api/v1/repositories/{repository_id}")
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "repository_not_found"

    regrant = await client.post(
        f"/api/v1/repositories/{repository_id}/members", json={"user_id": member["id"]}
    )
    assert regrant.status_code == 201

    restored = await second_client.get(f"/api/v1/repositories/{repository_id}")
    assert restored.status_code == 200


async def test_viewer_cannot_manage_repository_permissions(
    client: AsyncClient, second_client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    org_id = await _register_and_get_org_id(client, "permviewerowner@example.com")
    await _register(second_client, "permviewer@example.com")
    repository_id = await _connect_a_repository(client, org_id, httpx_mock)
    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "permviewer@example.com", "role": "viewer"},
    )

    response = await second_client.get(f"/api/v1/repositories/{repository_id}/members")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_role"


async def test_cannot_grant_access_to_a_non_member(
    client: AsyncClient, second_client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    org_id = await _register_and_get_org_id(client, "permgrantowner@example.com")
    outsider = await _register(second_client, "permoutsider@example.com")
    repository_id = await _connect_a_repository(client, org_id, httpx_mock)

    response = await client.post(
        f"/api/v1/repositories/{repository_id}/members", json={"user_id": outsider["id"]}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"
