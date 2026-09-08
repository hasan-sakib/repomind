import httpx

from app.integrations.github.schemas import (
    GitHubBranch,
    GitHubCommit,
    GitHubIssue,
    GitHubPullRequest,
    GitHubRepo,
)

API_BASE = "https://api.github.com"

# Bounded page sizes — a dashboard overview doesn't need full history.
# See docs/architecture/0003-github-integration.md for the tradeoff.
MAX_COMMITS = 50
MAX_PULL_REQUESTS = 50
MAX_ISSUES = 50


class GitHubAPIError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


def _headers(installation_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {installation_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _get(client: httpx.AsyncClient, path: str, **params: str | int) -> httpx.Response:
    response = await client.get(path, params=params)
    if response.status_code != 200:
        raise GitHubAPIError(response.status_code, f"GET {path} failed: {response.text}")
    return response


async def list_installation_repositories(installation_token: str) -> list[GitHubRepo]:
    repos: list[GitHubRepo] = []
    async with httpx.AsyncClient(
        base_url=API_BASE, headers=_headers(installation_token), timeout=15.0
    ) as client:
        page = 1
        while True:
            response = await _get(client, "/installation/repositories", per_page=100, page=page)
            body = response.json()
            repos.extend(GitHubRepo.from_api(r) for r in body["repositories"])
            if len(body["repositories"]) < 100:
                break
            page += 1
    return repos


async def get_repository(installation_token: str, full_name: str) -> GitHubRepo:
    async with httpx.AsyncClient(
        base_url=API_BASE, headers=_headers(installation_token), timeout=15.0
    ) as client:
        response = await _get(client, f"/repos/{full_name}")
    return GitHubRepo.from_api(response.json())


async def list_branches(installation_token: str, full_name: str) -> list[GitHubBranch]:
    async with httpx.AsyncClient(
        base_url=API_BASE, headers=_headers(installation_token), timeout=15.0
    ) as client:
        response = await _get(client, f"/repos/{full_name}/branches", per_page=100)
    return [GitHubBranch.from_api(b) for b in response.json()]


async def list_commits(
    installation_token: str, full_name: str, *, branch: str
) -> list[GitHubCommit]:
    async with httpx.AsyncClient(
        base_url=API_BASE, headers=_headers(installation_token), timeout=15.0
    ) as client:
        response = await _get(
            client, f"/repos/{full_name}/commits", sha=branch, per_page=MAX_COMMITS
        )
    return [GitHubCommit.from_api(c) for c in response.json()]


async def list_pull_requests(installation_token: str, full_name: str) -> list[GitHubPullRequest]:
    async with httpx.AsyncClient(
        base_url=API_BASE, headers=_headers(installation_token), timeout=15.0
    ) as client:
        response = await _get(
            client,
            f"/repos/{full_name}/pulls",
            state="all",
            sort="updated",
            direction="desc",
            per_page=MAX_PULL_REQUESTS,
        )
    return [GitHubPullRequest.from_api(p) for p in response.json()]


async def list_issues(installation_token: str, full_name: str) -> list[GitHubIssue]:
    async with httpx.AsyncClient(
        base_url=API_BASE, headers=_headers(installation_token), timeout=15.0
    ) as client:
        response = await _get(
            client,
            f"/repos/{full_name}/issues",
            state="all",
            sort="updated",
            direction="desc",
            per_page=MAX_ISSUES,
        )
    return [GitHubIssue.from_api(i) for i in response.json() if not GitHubIssue.is_pull_request(i)]
