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


async def _org_id(client: AsyncClient) -> str:
    me = await client.get("/api/v1/auth/me")
    return me.json()["organizations"][0]["organization"]["id"]


async def test_owner_can_create_and_list_an_api_key(client: AsyncClient) -> None:
    await _register(client, "keyowner@example.com")
    org_id = await _org_id(client)

    create = await client.post(
        f"/api/v1/organizations/{org_id}/api-keys",
        json={"name": "CI bot", "role": "viewer"},
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["name"] == "CI bot"
    assert body["role"] == "viewer"
    assert body["secret"].startswith("rm_")
    assert body["key_prefix"] in body["secret"]
    assert body["revoked_at"] is None

    listed = await client.get(f"/api/v1/organizations/{org_id}/api-keys")
    assert listed.status_code == 200
    keys = listed.json()
    assert len(keys) == 1
    assert "secret" not in keys[0]


async def test_admin_cannot_create_a_key_with_a_higher_role_than_their_own(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    await _register(client, "keyorgowner@example.com")
    await _register(second_client, "keyadmin@example.com")
    org_id = await _org_id(client)
    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "keyadmin@example.com", "role": "admin"},
    )

    response = await second_client.post(
        f"/api/v1/organizations/{org_id}/api-keys",
        json={"name": "Escalation attempt", "role": "owner"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_role"


async def test_viewer_cannot_manage_api_keys(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    await _register(client, "keyviewerorg@example.com")
    await _register(second_client, "keyviewer@example.com")
    org_id = await _org_id(client)
    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "keyviewer@example.com", "role": "viewer"},
    )

    response = await second_client.post(
        f"/api/v1/organizations/{org_id}/api-keys",
        json={"name": "Nope", "role": "viewer"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_role"


async def test_revoked_key_no_longer_authenticates(
    client: AsyncClient, second_client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    org_id = await _register_and_get_org_id(client, "keyrevoke@example.com")
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
    repository_id = connect_response.json()["id"]

    create = await client.post(
        f"/api/v1/organizations/{org_id}/api-keys",
        json={"name": "Read-only bot", "role": "viewer"},
    )
    secret = create.json()["secret"]
    api_key_id = create.json()["id"]

    # second_client never logged in — it has no session cookie at all, so
    # a 200 here can only come from the Authorization header.
    authed = await second_client.get(
        f"/api/v1/repositories/{repository_id}",
        headers={"Authorization": f"Bearer {secret}"},
    )
    assert authed.status_code == 200, authed.text

    revoke = await client.delete(f"/api/v1/organizations/{org_id}/api-keys/{api_key_id}")
    assert revoke.status_code == 204

    after_revoke = await second_client.get(
        f"/api/v1/repositories/{repository_id}",
        headers={"Authorization": f"Bearer {secret}"},
    )
    assert after_revoke.status_code == 401
    assert after_revoke.json()["error"]["code"] == "not_authenticated"


async def test_api_key_from_a_different_organization_cannot_read_this_repository(
    client: AsyncClient, second_client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    org_id = await _register_and_get_org_id(client, "keyscopeowner@example.com")
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
    repository_id = connect_response.json()["id"]

    other_org_id = await _register_and_get_org_id(second_client, "keyscopeother@example.com")
    other_key = await second_client.post(
        f"/api/v1/organizations/{other_org_id}/api-keys",
        json={"name": "Outsider bot", "role": "viewer"},
    )
    secret = other_key.json()["secret"]

    response = await client.get(
        f"/api/v1/repositories/{repository_id}",
        headers={"Authorization": f"Bearer {secret}"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "repository_not_found"
