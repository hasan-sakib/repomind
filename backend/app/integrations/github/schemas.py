from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class GitHubRepo:
    id: int
    full_name: str
    name: str
    description: str | None
    language: str | None
    stargazers_count: int
    forks_count: int
    default_branch: str
    private: bool
    html_url: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "GitHubRepo":
        return cls(
            id=data["id"],
            full_name=data["full_name"],
            name=data["name"],
            description=data.get("description"),
            language=data.get("language"),
            stargazers_count=data.get("stargazers_count", 0),
            forks_count=data.get("forks_count", 0),
            default_branch=data.get("default_branch", "main"),
            private=data.get("private", False),
            html_url=data["html_url"],
        )


@dataclass(frozen=True, slots=True)
class GitHubBranch:
    name: str
    commit_sha: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "GitHubBranch":
        return cls(name=data["name"], commit_sha=data["commit"]["sha"])


@dataclass(frozen=True, slots=True)
class GitHubCommit:
    sha: str
    message: str
    author_name: str | None
    author_login: str | None
    html_url: str
    authored_at: datetime

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "GitHubCommit":
        commit = data["commit"]
        author = data.get("author") or {}
        return cls(
            sha=data["sha"],
            message=commit["message"],
            author_name=commit.get("author", {}).get("name"),
            author_login=author.get("login"),
            html_url=data["html_url"],
            authored_at=_parse_datetime(commit["author"]["date"]),
        )


@dataclass(frozen=True, slots=True)
class GitHubPullRequest:
    number: int
    title: str
    state: str
    author_login: str | None
    html_url: str
    head_sha: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    merged_at: datetime | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "GitHubPullRequest":
        user = data.get("user") or {}
        return cls(
            number=data["number"],
            title=data["title"],
            state=data["state"],
            author_login=user.get("login"),
            html_url=data["html_url"],
            head_sha=data["head"]["sha"],
            created_at=_parse_datetime(data["created_at"]),
            updated_at=_parse_datetime(data["updated_at"]),
            closed_at=_parse_datetime(data["closed_at"]) if data.get("closed_at") else None,
            merged_at=_parse_datetime(data["merged_at"]) if data.get("merged_at") else None,
        )


@dataclass(frozen=True, slots=True)
class GitHubPullRequestFile:
    """One entry from `GET /pulls/{number}/files` — the actual diff. `patch`
    is the unified-diff hunk text; GitHub omits it for binary files and for
    files past an internal size cutoff, so it's optional even when the
    file itself is a genuine part of the PR."""

    filename: str
    status: str  # added | removed | modified | renamed | copied | changed | unchanged
    additions: int
    deletions: int
    changes: int
    patch: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "GitHubPullRequestFile":
        return cls(
            filename=data["filename"],
            status=data["status"],
            additions=data.get("additions", 0),
            deletions=data.get("deletions", 0),
            changes=data.get("changes", 0),
            patch=data.get("patch"),
        )


@dataclass(frozen=True, slots=True)
class GitHubIssue:
    number: int
    title: str
    state: str
    author_login: str | None
    html_url: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "GitHubIssue":
        user = data.get("user") or {}
        return cls(
            number=data["number"],
            title=data["title"],
            state=data["state"],
            author_login=user.get("login"),
            html_url=data["html_url"],
            created_at=_parse_datetime(data["created_at"]),
            updated_at=_parse_datetime(data["updated_at"]),
            closed_at=_parse_datetime(data["closed_at"]) if data.get("closed_at") else None,
        )

    @staticmethod
    def is_pull_request(data: dict[str, Any]) -> bool:
        """GitHub's /issues endpoint also returns pull requests. Callers
        must filter these out before treating a row as a real issue."""
        return "pull_request" in data


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
