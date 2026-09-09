import httpx

from app.integrations.github.schemas import (
    GitHubBranch,
    GitHubCommit,
    GitHubIssue,
    GitHubPullRequest,
    GitHubPullRequestFile,
    GitHubRepo,
)

API_BASE = "https://api.github.com"

# Bounded page sizes — a dashboard overview doesn't need full history.
# See docs/architecture/0003-github-integration.md for the tradeoff.
MAX_COMMITS = 50
MAX_PULL_REQUESTS = 50
MAX_ISSUES = 50
MAX_PULL_REQUEST_FILES = 100


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


async def _get(client: httpx.AsyncClient, url: str, **params: str | int) -> httpx.Response:
    # Named `url`, not `path` — a caller needs to pass GitHub's own `path`
    # *query* parameter through **params (list_commits_for_path, filtering
    # commits by file path), which would collide with this parameter's
    # name otherwise.
    response = await client.get(url, params=params)
    if response.status_code != 200:
        raise GitHubAPIError(response.status_code, f"GET {url} failed: {response.text}")
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


async def list_commits_for_path(
    installation_token: str, full_name: str, *, branch: str, file_path: str, limit: int = 10
) -> list[GitHubCommit]:
    """ "Recent changes" for one file (app/architecture/graph_builder.py's
    node detail) — fetched live via GitHub's own `path` filter rather than
    stored, since Commit rows (ADR 0003) have no per-commit changed-file
    list to query locally."""
    async with httpx.AsyncClient(
        base_url=API_BASE, headers=_headers(installation_token), timeout=15.0
    ) as client:
        response = await _get(
            client, f"/repos/{full_name}/commits", sha=branch, path=file_path, per_page=limit
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


async def list_pull_request_files(
    installation_token: str, full_name: str, *, number: int
) -> list[GitHubPullRequestFile]:
    """The PR's actual diff — one entry per changed file, with the unified
    patch text where GitHub provides one. Bounded to
    MAX_PULL_REQUEST_FILES (GitHub itself caps this endpoint at 3000 files
    and paginates at 30/page by default); a PR touching more files than
    that gets analyzed on its first MAX_PULL_REQUEST_FILES only — see
    docs/architecture/0007-ai-pull-request-intelligence.md."""
    async with httpx.AsyncClient(
        base_url=API_BASE, headers=_headers(installation_token), timeout=15.0
    ) as client:
        response = await _get(
            client, f"/repos/{full_name}/pulls/{number}/files", per_page=MAX_PULL_REQUEST_FILES
        )
    return [GitHubPullRequestFile.from_api(f) for f in response.json()]


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
