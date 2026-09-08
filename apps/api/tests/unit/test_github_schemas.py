from app.integrations.github.schemas import GitHubCommit, GitHubIssue, GitHubRepo


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
