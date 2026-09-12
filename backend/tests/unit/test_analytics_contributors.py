import uuid
from datetime import UTC, datetime

from app.analytics.contributors import build_contributor_activity
from app.models.pull_request import PullRequest


def _daily_commit(login: str | None, name: str | None, count: int, date: str = "2026-01-01"):
    return {"date": date, "login": login, "name": name, "count": count}


def _pr(author_login: str | None) -> PullRequest:
    return PullRequest(
        id=uuid.uuid4(),
        repository_id=uuid.uuid4(),
        number=1,
        title="PR",
        state="open",
        author_login=author_login,
        html_url="https://github.com/acme/widgets/pull/1",
        head_sha="f" * 40,
        github_created_at=datetime(2026, 1, 1, tzinfo=UTC),
        github_updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        closed_at=None,
        merged_at=None,
        synced_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_combines_commit_and_pr_counts_per_contributor() -> None:
    daily_commits = [
        _daily_commit("ada", "Ada", 3, "2026-01-01"),
        _daily_commit("ada", "Ada", 2, "2026-01-02"),
        _daily_commit("grace", "Grace", 1, "2026-01-01"),
    ]
    pull_requests = [_pr("ada"), _pr("ada"), _pr("grace")]

    activity = build_contributor_activity(daily_commits, pull_requests)

    by_login = {r["login"]: r for r in activity}
    assert by_login["ada"]["commit_count"] == 5
    assert by_login["ada"]["pr_count"] == 2
    assert by_login["grace"]["commit_count"] == 1
    assert by_login["grace"]["pr_count"] == 1


def test_sorted_by_total_activity_descending() -> None:
    daily_commits = [_daily_commit("ada", "Ada", 1), _daily_commit("grace", "Grace", 10)]
    activity = build_contributor_activity(daily_commits, [])
    assert [r["login"] for r in activity] == ["grace", "ada"]


def test_contributor_with_only_prs_and_no_commits_is_included() -> None:
    activity = build_contributor_activity([], [_pr("ada")])
    assert len(activity) == 1
    assert activity[0]["login"] == "ada"
    assert activity[0]["commit_count"] == 0


def test_name_is_backfilled_from_any_commit_record_that_has_one() -> None:
    daily_commits = [
        _daily_commit("ada", None, 1, "2026-01-01"),
        _daily_commit("ada", "Ada Lovelace", 1, "2026-01-02"),
    ]
    activity = build_contributor_activity(daily_commits, [])
    assert activity[0]["name"] == "Ada Lovelace"


def test_empty_input_yields_empty_list() -> None:
    assert build_contributor_activity([], []) == []
