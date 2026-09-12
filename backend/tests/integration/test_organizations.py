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


async def _personal_org_id(client: AsyncClient) -> str:
    me = await client.get("/api/v1/auth/me")
    return me.json()["organizations"][0]["organization"]["id"]


async def test_create_organization(client: AsyncClient) -> None:
    await _register(client, "creator@example.com")
    response = await client.post("/api/v1/organizations", json={"name": "Acme Corp"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Acme Corp"
    assert body["slug"] == "acme-corp"


async def test_list_my_organizations_includes_personal_and_created(client: AsyncClient) -> None:
    await _register(client, "lister@example.com")
    await client.post("/api/v1/organizations", json={"name": "Second Org"})
    response = await client.get("/api/v1/organizations")
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_owner_can_add_member(client: AsyncClient, second_client: AsyncClient) -> None:
    await _register(client, "owner1@example.com")
    member_user = await _register(second_client, "member1@example.com")
    org_id = await _personal_org_id(client)

    response = await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "member1@example.com", "role": "developer"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "developer"
    assert body["user"]["id"] == member_user["id"]


async def test_add_member_requires_admin_role(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    await _register(client, "owner2@example.com")
    await _register(second_client, "viewer2@example.com")
    org_id = await _personal_org_id(client)

    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "viewer2@example.com", "role": "viewer"},
    )

    # viewer2 is only a viewer in org_id — cannot add members.
    response = await second_client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "owner2@example.com", "role": "developer"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_role"


async def test_add_member_nonexistent_user_returns_404(client: AsyncClient) -> None:
    await _register(client, "owner3@example.com")
    org_id = await _personal_org_id(client)
    response = await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "nobody-registered@example.com", "role": "developer"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"


async def test_add_member_already_a_member_returns_409(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    await _register(client, "owner4@example.com")
    await _register(second_client, "member4@example.com")
    org_id = await _personal_org_id(client)

    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "member4@example.com", "role": "developer"},
    )
    duplicate = await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "member4@example.com", "role": "viewer"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "member_already_exists"


async def test_only_owner_can_grant_owner_role(
    client: AsyncClient, second_client: AsyncClient, third_client: AsyncClient
) -> None:
    await _register(client, "owner5@example.com")
    await _register(second_client, "admin5@example.com")
    await _register(third_client, "third5@example.com")
    org_id = await _personal_org_id(client)

    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "admin5@example.com", "role": "admin"},
    )

    # admin5 is ADMIN, not OWNER — cannot grant the owner role to anyone.
    response = await second_client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "third5@example.com", "role": "owner"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_role"


async def test_update_member_role(client: AsyncClient, second_client: AsyncClient) -> None:
    await _register(client, "owner6@example.com")
    member_user = await _register(second_client, "member6@example.com")
    org_id = await _personal_org_id(client)

    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "member6@example.com", "role": "viewer"},
    )
    response = await client.patch(
        f"/api/v1/organizations/{org_id}/members/{member_user['id']}",
        json={"role": "admin"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


async def test_cannot_demote_last_owner(client: AsyncClient) -> None:
    await _register(client, "soleowner@example.com")
    org_id = await _personal_org_id(client)
    me = await client.get("/api/v1/auth/me")
    user_id = me.json()["user"]["id"]

    response = await client.patch(
        f"/api/v1/organizations/{org_id}/members/{user_id}", json={"role": "admin"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "last_owner"


async def test_member_can_remove_self(client: AsyncClient, second_client: AsyncClient) -> None:
    await _register(client, "owner7@example.com")
    member_user = await _register(second_client, "member7@example.com")
    org_id = await _personal_org_id(client)

    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "member7@example.com", "role": "viewer"},
    )
    response = await second_client.delete(
        f"/api/v1/organizations/{org_id}/members/{member_user['id']}"
    )
    assert response.status_code == 204

    # No longer a member — org is now invisible to them.
    check = await second_client.get(f"/api/v1/organizations/{org_id}/members")
    assert check.status_code == 404


async def test_removing_someone_else_requires_admin(
    client: AsyncClient, second_client: AsyncClient, third_client: AsyncClient
) -> None:
    await _register(client, "owner8@example.com")
    await _register(second_client, "member8@example.com")
    third_user = await _register(third_client, "member8b@example.com")
    org_id = await _personal_org_id(client)

    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "member8@example.com", "role": "viewer"},
    )
    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "member8b@example.com", "role": "viewer"},
    )
    # member8 (viewer) tries to remove member8b (a different member) — not allowed.
    response = await second_client.delete(
        f"/api/v1/organizations/{org_id}/members/{third_user['id']}"
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_role"


async def test_cannot_remove_last_owner(client: AsyncClient) -> None:
    await _register(client, "soleowner2@example.com")
    org_id = await _personal_org_id(client)
    me = await client.get("/api/v1/auth/me")
    user_id = me.json()["user"]["id"]

    response = await client.delete(f"/api/v1/organizations/{org_id}/members/{user_id}")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "last_owner"


async def test_non_member_gets_not_found_not_forbidden(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    await _register(client, "owner9@example.com")
    await _register(second_client, "outsider9@example.com")
    org_id = await _personal_org_id(client)

    # outsider9 is not a member of client's org at all.
    response = await second_client.get(f"/api/v1/organizations/{org_id}/members")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "organization_not_found"
