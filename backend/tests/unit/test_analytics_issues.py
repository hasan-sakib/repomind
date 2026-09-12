import uuid
from datetime import UTC, datetime

from app.analytics.issues import bucket_daily_issue_counts, summarize_open_issues
from app.domain.issue import Issue


def _issue(
    number: int, *, created: datetime, state: str = "open", closed: datetime | None = None
) -> Issue:
    return Issue(
        id=uuid.uuid4(),
        repository_id=uuid.uuid4(),
        number=number,
        title=f"Issue {number}",
        state=state,
        author_login="ada",
        html_url=f"https://github.com/acme/widgets/issues/{number}",
        github_created_at=created,
        github_updated_at=closed or created,
        closed_at=closed,
        synced_at=created,
    )


def test_bucket_daily_issue_counts_by_creation_date() -> None:
    issues = [
        _issue(1, created=datetime(2026, 1, 1, tzinfo=UTC)),
        _issue(2, created=datetime(2026, 1, 1, tzinfo=UTC)),
        _issue(3, created=datetime(2026, 1, 2, tzinfo=UTC)),
    ]
    counts = bucket_daily_issue_counts(issues)
    assert counts == {"2026-01-01": 2, "2026-01-02": 1}


def test_summarize_open_issues_counts_only_open_state() -> None:
    now = datetime(2026, 2, 1, tzinfo=UTC)
    issues = [
        _issue(1, created=datetime(2026, 1, 1, tzinfo=UTC), state="open"),
        _issue(2, created=datetime(2026, 1, 1, tzinfo=UTC), state="closed", closed=now),
    ]
    total, _ = summarize_open_issues(issues, now=now, stale_after_days=30, limit=10)
    assert total == 1


def test_summarize_open_issues_flags_only_issues_older_than_threshold() -> None:
    now = datetime(2026, 2, 1, tzinfo=UTC)
    issues = [
        _issue(1, created=datetime(2026, 1, 31, tzinfo=UTC), state="open"),  # 1 day old
        _issue(2, created=datetime(2025, 1, 1, tzinfo=UTC), state="open"),  # over a year old
    ]
    _, stale = summarize_open_issues(issues, now=now, stale_after_days=30, limit=10)
    assert [s["number"] for s in stale] == [2]


def test_summarize_open_issues_sorted_oldest_first_and_respects_limit() -> None:
    now = datetime(2026, 2, 1, tzinfo=UTC)
    issues = [
        _issue(1, created=datetime(2025, 6, 1, tzinfo=UTC), state="open"),
        _issue(2, created=datetime(2025, 1, 1, tzinfo=UTC), state="open"),
        _issue(3, created=datetime(2025, 3, 1, tzinfo=UTC), state="open"),
    ]
    _, stale = summarize_open_issues(issues, now=now, stale_after_days=30, limit=2)
    assert len(stale) == 2
    assert [s["number"] for s in stale] == [2, 3]


def test_no_issues_yields_zero_and_empty() -> None:
    total, stale = summarize_open_issues(
        [], now=datetime(2026, 1, 1, tzinfo=UTC), stale_after_days=30, limit=10
    )
    assert total == 0
    assert stale == []
