from datetime import UTC, datetime, timedelta

import httpx
import jwt

from app.core.config import get_settings

settings = get_settings()

APP_JWT_TTL_MINUTES = 9  # GitHub allows at most 10 minutes; stay under it.


class GitHubAppError(Exception):
    """Raised when App-level JWT minting or installation token exchange fails."""


def mint_app_jwt() -> str:
    """A short-lived JWT identifying the GitHub App itself (not any
    installation), signed with the App's private key. Used only to
    request installation access tokens — never sent anywhere else."""
    now = datetime.now(UTC)
    payload = {
        "iat": int((now - timedelta(seconds=60)).timestamp()),  # clock drift tolerance
        "exp": int((now + timedelta(minutes=APP_JWT_TTL_MINUTES)).timestamp()),
        "iss": settings.github_app_id,
    }
    return jwt.encode(payload, settings.github_app_private_key, algorithm="RS256")


async def get_installation_access_token(installation_id: int) -> str:
    """Mints a fresh installation access token (~1hr validity) on every
    call — no caching in this phase (would need Redis; see
    docs/architecture/0003-github-integration.md for why that's deferred).
    """
    app_jwt = mint_app_jwt()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
            },
        )
    if response.status_code != 201:
        raise GitHubAppError(
            f"Failed to mint installation token for {installation_id}: "
            f"{response.status_code} {response.text}"
        )
    token = response.json().get("token")
    if not token:
        raise GitHubAppError(f"Installation token response had no token: {response.json()}")
    return str(token)


async def get_installation_account(installation_id: int) -> tuple[str, str]:
    """Returns (account_login, account_type) for an installation — used
    right after the install callback, before any installation token
    exists, so this is authenticated with the App-level JWT instead."""
    app_jwt = mint_app_jwt()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"https://api.github.com/app/installations/{installation_id}",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
            },
        )
    if response.status_code != 200:
        raise GitHubAppError(
            f"Failed to fetch installation {installation_id}: "
            f"{response.status_code} {response.text}"
        )
    body = response.json()
    account = body["account"]
    return account["login"], account["type"]
