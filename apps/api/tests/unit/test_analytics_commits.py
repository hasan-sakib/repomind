from datetime import UTC, datetime

from app.analytics.commits import bucket_daily_commits
from app.integrations.github.schemas import GitHubCommit


def _commit(sha: str, *, login: str | None, name: str | None, when: datetime) -> GitHubCommit:
    return GitHubCommit(
        sha=sha,
        message="msg",
        author_name=name,
        author_login=login,
        html_url=f"https://github.com/acme/widgets/commit/{sha}",
        authored_at=when,
    )


def test_buckets_by_day_and_author() -> None:
    commits = [
        _commit("a", login="ada", name="Ada", when=datetime(2026, 1, 1, 9, tzinfo=UTC)),
        _commit("b", login="ada", name="Ada", when=datetime(2026, 1, 1, 15, tzinfo=UTC)),
        _commit("c", login="grace", name="Grace", when=datetime(2026, 1, 1, 10, tzinfo=UTC)),
        _commit("d", login="ada", name="Ada", when=datetime(2026, 1, 2, 9, tzinfo=UTC)),
    ]

    records = bucket_daily_commits(commits)

    by_key = {(r["date"], r["login"]): r["count"] for r in records}
    assert by_key[("2026-01-01", "ada")] == 2
    assert by_key[("2026-01-01", "grace")] == 1
    assert by_key[("2026-01-02", "ada")] == 1


def test_records_are_sorted_by_date_then_login() -> None:
    commits = [
        _commit("a", login="zed", name="Zed", when=datetime(2026, 1, 2, tzinfo=UTC)),
        _commit("b", login="ada", name="Ada", when=datetime(2026, 1, 1, tzinfo=UTC)),
    ]
    records = bucket_daily_commits(commits)
    assert [r["date"] for r in records] == ["2026-01-01", "2026-01-02"]


def test_handles_commits_with_no_linked_github_account() -> None:
    commits = [_commit("a", login=None, name="Someone", when=datetime(2026, 1, 1, tzinfo=UTC))]
    records = bucket_daily_commits(commits)
    assert records == [{"date": "2026-01-01", "login": None, "name": "Someone", "count": 1}]


def test_empty_input_yields_empty_list() -> None:
    assert bucket_daily_commits([]) == []
