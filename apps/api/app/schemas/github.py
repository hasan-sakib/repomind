import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.branch import Branch
from app.domain.commit import Commit
from app.domain.github_installation import GitHubInstallation
from app.domain.issue import Issue
from app.domain.pull_request import PullRequest
from app.domain.repository import Repository
from app.domain.repository_status import RepositoryStatus
from app.integrations.github.schemas import GitHubRepo


class InstallationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_login: str
    account_type: str


class AvailableRepositoryPublic(BaseModel):
    github_repo_id: int
    full_name: str
    name: str
    private: bool
    description: str | None

    @classmethod
    def from_github_repo(cls, repo: GitHubRepo) -> "AvailableRepositoryPublic":
        return cls(
            github_repo_id=repo.id,
            full_name=repo.full_name,
            name=repo.name,
            private=repo.private,
            description=repo.description,
        )


class ConnectRepositoryRequest(BaseModel):
    installation_id: uuid.UUID
    github_repo_id: int
    full_name: str


class RepositoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    name: str
    description: str | None
    language: str | None
    stargazers_count: int
    forks_count: int
    default_branch: str
    private: bool
    html_url: str
    status: RepositoryStatus
    sync_error: str | None
    last_synced_at: datetime | None
    connected_at: datetime

    @classmethod
    def from_repository(cls, repository: Repository) -> "RepositoryPublic":
        return cls.model_validate(repository)


class BranchPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    commit_sha: str
    is_default: bool

    @classmethod
    def from_branch(cls, branch: Branch) -> "BranchPublic":
        return cls.model_validate(branch)


class CommitPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sha: str
    message: str
    author_name: str | None
    author_login: str | None
    html_url: str
    authored_at: datetime

    @classmethod
    def from_commit(cls, commit: Commit) -> "CommitPublic":
        return cls.model_validate(commit)


class PullRequestPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: int
    title: str
    state: str
    author_login: str | None
    html_url: str
    github_created_at: datetime
    github_updated_at: datetime
    closed_at: datetime | None
    merged_at: datetime | None

    @classmethod
    def from_pull_request(cls, pr: PullRequest) -> "PullRequestPublic":
        return cls.model_validate(pr)


class IssuePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: int
    title: str
    state: str
    author_login: str | None
    html_url: str
    github_created_at: datetime
    github_updated_at: datetime
    closed_at: datetime | None

    @classmethod
    def from_issue(cls, issue: Issue) -> "IssuePublic":
        return cls.model_validate(issue)


class RepositoryOverview(BaseModel):
    """The repository-detail response — everything the overview page
    needs in one call: repo metadata + recent commits + open PRs + open
    issues, so the frontend doesn't need four round trips."""

    repository: RepositoryPublic
    recent_commits: list[CommitPublic]
    open_pull_requests: list[PullRequestPublic]
    open_issues: list[IssuePublic]


def installation_public(installation: GitHubInstallation) -> InstallationPublic:
    return InstallationPublic.model_validate(installation)
