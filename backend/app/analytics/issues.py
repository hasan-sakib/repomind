"""Open-issue aggregation from already-synced Issue rows (ADR 0003's
bounded window) — no extra GitHub calls."""

from datetime import datetime

from app.models.analytics_snapshot import StaleIssueRecord
from app.models.issue import Issue


def bucket_daily_issue_counts(issues: list[Issue]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for issue in issues:
        date = issue.github_created_at.date().isoformat()
        counts[date] = counts.get(date, 0) + 1
    return counts


def summarize_open_issues(
    issues: list[Issue], *, now: datetime, stale_after_days: int, limit: int
) -> tuple[int, list[StaleIssueRecord]]:
    open_issues = [i for i in issues if i.state == "open"]

    stale = sorted(
        (
            StaleIssueRecord(
                number=i.number,
                title=i.title,
                html_url=i.html_url,
                age_days=(now - i.github_created_at).days,
            )
            for i in open_issues
            if (now - i.github_created_at).days >= stale_after_days
        ),
        key=lambda s: s["age_days"],
        reverse=True,
    )
    return len(open_issues), stale[:limit]
