import re

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register(
    client: AsyncClient, email: str, password: str = "correct-horse-battery"
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert response.status_code == 201, response.text


async def test_register_creates_user_and_personal_organization(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "password": "correct-horse-battery",
            "full_name": "Alice Example",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["email_verified"] is False
    assert "rm_session" in response.cookies
    assert "rm_refresh" in response.cookies

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    me_body = me.json()
    assert len(me_body["organizations"]) == 1
    assert me_body["organizations"][0]["role"] == "owner"


async def test_register_duplicate_email_is_rejected(client: AsyncClient) -> None:
    await _register(client, "dup@example.com")
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "another-password", "full_name": "Dup"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_already_registered"


async def test_login_success(client: AsyncClient) -> None:
    await _register(client, "login@example.com", "the-right-password")
    await client.post("/api/v1/auth/logout")
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "the-right-password"},
    )
    assert response.status_code == 200
    assert "rm_session" in response.cookies


async def test_login_wrong_password_rejected(client: AsyncClient) -> None:
    await _register(client, "wrongpw@example.com", "the-right-password")
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "not-the-right-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_login_nonexistent_email_gives_same_generic_error(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


async def test_logout_without_csrf_header_is_rejected(client: AsyncClient) -> None:
    await _register(client, "csrf@example.com")
    response = await client.post("/api/v1/auth/logout", headers={"X-Requested-With": ""})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


async def test_logout_revokes_session(client: AsyncClient) -> None:
    await _register(client, "logout@example.com")
    logout_response = await client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 401


async def test_refresh_rotates_token_and_reuse_is_detected(client: AsyncClient) -> None:
    await _register(client, "refresh@example.com")
    old_refresh_cookie = client.cookies.get("rm_refresh")

    refresh_response = await client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 204
    new_refresh_cookie = client.cookies.get("rm_refresh")
    assert new_refresh_cookie != old_refresh_cookie

    # Reusing the old (already-rotated) refresh token must fail...
    client.cookies.set("rm_refresh", old_refresh_cookie)
    reuse_response = await client.post("/api/v1/auth/refresh")
    assert reuse_response.status_code == 401
    assert reuse_response.json()["error"]["code"] == "invalid_or_expired_token"

    # ...and must have revoked the whole session, so even the freshly
    # rotated token from the successful refresh above no longer works.
    client.cookies.set("rm_refresh", new_refresh_cookie)
    after_theft_response = await client.post("/api/v1/auth/refresh")
    assert after_theft_response.status_code == 401


async def test_password_reset_flow(
    client: AsyncClient, captured_emails: list[dict[str, str]]
) -> None:
    await _register(client, "reset@example.com", "old-password")
    await client.post("/api/v1/auth/logout")

    request_response = await client.post(
        "/api/v1/auth/password-reset/request", json={"email": "reset@example.com"}
    )
    assert request_response.status_code == 204
    # Registration already sent a verification email — the reset request
    # sends a second, distinct one.
    assert len(captured_emails) == 2
    reset_email = captured_emails[-1]
    assert reset_email["subject"] == "Reset your RepoMind password"
    token_match = re.search(r"token=(\S+)", reset_email["body"])
    assert token_match is not None
    token = token_match.group(1)

    confirm_response = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "brand-new-password"},
    )
    assert confirm_response.status_code == 204

    old_login = await client.post(
        "/api/v1/auth/login", json={"email": "reset@example.com", "password": "old-password"}
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "brand-new-password"},
    )
    assert new_login.status_code == 200


async def test_password_reset_request_for_unknown_email_still_returns_204(
    client: AsyncClient, captured_emails: list[dict[str, str]]
) -> None:
    response = await client.post(
        "/api/v1/auth/password-reset/request", json={"email": "ghost@example.com"}
    )
    assert response.status_code == 204
    assert captured_emails == []


async def test_email_verification_flow(
    client: AsyncClient, captured_emails: list[dict[str, str]]
) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "verify@example.com",
            "password": "correct-horse-battery",
            "full_name": "Verify Me",
        },
    )
    assert len(captured_emails) == 1
    token_match = re.search(r"token=(\S+)", captured_emails[0]["body"])
    assert token_match is not None

    confirm_response = await client.post(
        "/api/v1/auth/email/verify/confirm", json={"token": token_match.group(1)}
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["email_verified"] is True


async def test_email_verification_rejects_invalid_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/email/verify/confirm", json={"token": "not-a-real-token"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_or_expired_token"
