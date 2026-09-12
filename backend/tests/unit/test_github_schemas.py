from app.integrations.github.schemas import (
    GitHubCommit,
    GitHubIssue,
    GitHubPullRequest,
    GitHubPullRequestFile,
    GitHubRepo,
)


def test_github_repo_from_api_parses_expected_fields() -> None:
    repo = GitHubRepo.from_api(
        {
            "id": 42,
            "full_name": "acme/widgets",
            "name": "widgets",
            "description": "Widget factory",
            "language": "Python",
            "stargazers_count": 10,
            "forks_count": 2,
            "default_branch": "main",
            "private": False,
            "html_url": "https://github.com/acme/widgets",
        }
    )
    assert repo.id == 42
    assert repo.full_name == "acme/widgets"
    assert repo.language == "Python"


def test_github_repo_from_api_handles_missing_optional_fields() -> None:
    repo = GitHubRepo.from_api(
        {
            "id": 42,
            "full_name": "acme/widgets",
            "name": "widgets",
            "html_url": "https://github.com/acme/widgets",
        }
    )
    assert repo.description is None
    assert repo.language is None
    assert repo.stargazers_count == 0
    assert repo.default_branch == "main"


def test_github_commit_from_api_parses_author() -> None:
    commit = GitHubCommit.from_api(
        {
            "sha": "abc123",
            "html_url": "https://github.com/acme/widgets/commit/abc123",
            "commit": {
                "message": "Fix bug",
                "author": {"name": "Ada Lovelace", "date": "2026-01-01T00:00:00Z"},
            },
            "author": {"login": "ada"},
        }
    )
    assert commit.sha == "abc123"
    assert commit.author_name == "Ada Lovelace"
    assert commit.author_login == "ada"
    assert commit.authored_at.year == 2026


def test_github_commit_from_api_handles_missing_github_account() -> None:
    """A commit authored with an email not linked to any GitHub account has
    a null `author` — must not crash."""
    commit = GitHubCommit.from_api(
        {
            "sha": "abc123",
            "html_url": "https://github.com/acme/widgets/commit/abc123",
            "commit": {
                "message": "Fix bug",
                "author": {"name": "Ada Lovelace", "date": "2026-01-01T00:00:00Z"},
            },
            "author": None,
        }
    )
    assert commit.author_login is None


def test_issue_is_pull_request_detects_prs_in_issues_endpoint() -> None:
    assert GitHubIssue.is_pull_request({"pull_request": {"url": "..."}}) is True
    assert GitHubIssue.is_pull_request({"title": "A real issue"}) is False


def test_github_pull_request_from_api_parses_head_sha() -> None:
    pr = GitHubPullRequest.from_api(
        {
            "number": 183,
            "title": "Add refresh token rotation",
            "state": "open",
            "user": {"login": "ada"},
            "html_url": "https://github.com/acme/widgets/pull/183",
            "head": {"sha": "deadbeef" * 5},
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "closed_at": None,
            "merged_at": None,
        }
    )
    assert pr.head_sha == "deadbeef" * 5
    assert pr.author_login == "ada"


def test_github_pull_request_file_from_api_parses_patch() -> None:
    file = GitHubPullRequestFile.from_api(
        {
            "filename": "app/services/auth_service.py",
            "status": "modified",
            "additions": 10,
            "deletions": 2,
            "changes": 12,
            "patch": "@@ -1,1 +1,2 @@\n+    pass",
        }
    )
    assert file.filename == "app/services/auth_service.py"
    assert file.patch == "@@ -1,1 +1,2 @@\n+    pass"


def test_github_pull_request_file_from_api_handles_missing_patch() -> None:
    """GitHub omits `patch` for binary files and files past its internal
    size cutoff — must not crash."""
    file = GitHubPullRequestFile.from_api(
        {
            "filename": "assets/logo.png",
            "status": "added",
            "additions": 0,
            "deletions": 0,
            "changes": 0,
        }
    )
    assert file.patch is None
