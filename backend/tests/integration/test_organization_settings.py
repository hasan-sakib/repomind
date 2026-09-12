import pytest
from httpx import AsyncClient

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


async def test_owner_can_rename_organization(client: AsyncClient) -> None:
    await _register(client, "renamer@example.com")
    org_id = await _org_id(client)

    response = await client.patch(f"/api/v1/organizations/{org_id}", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"

    fetched = await client.get(f"/api/v1/organizations/{org_id}")
    assert fetched.json()["name"] == "New Name"


async def test_viewer_cannot_rename_organization(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    await _register(client, "renamer-owner@example.com")
    await _register(second_client, "renamer-viewer@example.com")
    org_id = await _org_id(client)
    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "renamer-viewer@example.com", "role": "viewer"},
    )

    response = await second_client.patch(
        f"/api/v1/organizations/{org_id}", json={"name": "Hijacked"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_role"


async def test_new_organization_starts_on_the_free_plan(client: AsyncClient) -> None:
    await _register(client, "freebie@example.com")
    org_id = await _org_id(client)
    response = await client.get(f"/api/v1/organizations/{org_id}")
    assert response.json()["plan"] == "free"


async def test_owner_can_change_plan(client: AsyncClient) -> None:
    await _register(client, "upgrader@example.com")
    org_id = await _org_id(client)

    response = await client.post(f"/api/v1/organizations/{org_id}/plan", json={"plan": "pro"})
    assert response.status_code == 200
    assert response.json()["plan"] == "pro"


async def test_admin_cannot_change_plan(client: AsyncClient, second_client: AsyncClient) -> None:
    await _register(client, "planowner@example.com")
    await _register(second_client, "planadmin@example.com")
    org_id = await _org_id(client)
    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "planadmin@example.com", "role": "admin"},
    )

    response = await second_client.post(
        f"/api/v1/organizations/{org_id}/plan", json={"plan": "team"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_role"


async def test_usage_reflects_repository_and_member_counts(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    await _register(client, "usageowner@example.com")
    await _register(second_client, "usagemember@example.com")
    org_id = await _org_id(client)
    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "usagemember@example.com", "role": "viewer"},
    )

    response = await client.get(f"/api/v1/organizations/{org_id}/usage")
    assert response.status_code == 200
    body = response.json()
    assert body["plan"] == "free"
    assert body["limits"]["max_repositories"] == 3
    assert body["repositories_used"] == 0
    assert body["members_used"] == 2  # owner + the member just added
    assert body["ai_tokens_used"] == 0


async def test_billing_catalog_lists_every_plan(client: AsyncClient) -> None:
    await _register(client, "cataloguer@example.com")
    org_id = await _org_id(client)

    response = await client.get(f"/api/v1/organizations/{org_id}/billing")
    assert response.status_code == 200
    body = response.json()
    assert body["current_plan"] == "free"
    assert body["is_billing_configured"] is False
    plans = {entry["plan"] for entry in body["plans"]}
    assert plans == {"free", "pro", "team"}


async def test_audit_logs_record_organization_creation_and_require_admin(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    await _register(client, "auditowner@example.com")
    await _register(second_client, "auditviewer@example.com")
    org_id = await _org_id(client)
    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "auditviewer@example.com", "role": "viewer"},
    )

    response = await client.get(f"/api/v1/organizations/{org_id}/audit-logs")
    assert response.status_code == 200
    actions = [entry["action"] for entry in response.json()]
    assert "organization.created" in actions
    assert "organization.member.added" in actions

    forbidden = await second_client.get(f"/api/v1/organizations/{org_id}/audit-logs")
    assert forbidden.status_code == 403
