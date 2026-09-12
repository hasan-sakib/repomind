from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

settings = get_settings()

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_API_URL = "https://api.github.com/user"
USER_EMAILS_API_URL = "https://api.github.com/user/emails"


class GitHubOAuthError(Exception):
    """Raised when the OAuth code exchange or profile fetch fails."""


@dataclass(frozen=True, slots=True)
class GitHubUser:
    id: int
    login: str
    avatar_url: str | None
    name: str | None


def build_authorize_url(*, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": redirect_uri,
        "scope": "read:user user:email",
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code_for_access_token(*, code: str, redirect_uri: str) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            ACCESS_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
    if response.status_code != 200:
        raise GitHubOAuthError(f"GitHub token exchange failed: {response.status_code}")

    body = response.json()
    access_token = body.get("access_token")
    if not access_token:
        raise GitHubOAuthError(f"GitHub token exchange returned no access_token: {body}")
    return str(access_token)


async def fetch_github_user(access_token: str) -> GitHubUser:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            USER_API_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
    if response.status_code != 200:
        raise GitHubOAuthError(f"GitHub user fetch failed: {response.status_code}")

    body = response.json()
    return GitHubUser(
        id=body["id"],
        login=body["login"],
        avatar_url=body.get("avatar_url"),
        name=body.get("name"),
    )


async def fetch_github_primary_email(access_token: str) -> str | None:
    """The /user endpoint's `email` field is null unless the user has made
    an email public, regardless of scope. The verified primary email (if
    any) is only available via this separate endpoint."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            USER_EMAILS_API_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
    if response.status_code != 200:
        raise GitHubOAuthError(f"GitHub email fetch failed: {response.status_code}")

    emails = response.json()
    for entry in emails:
        if entry.get("primary") and entry.get("verified"):
            return str(entry["email"])
    return None
