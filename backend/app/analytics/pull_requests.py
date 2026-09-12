"""PR throughput and cycle-time aggregation, computed entirely from
already-synced PullRequest rows (ADR 0003's bounded ~50-PR window) — no
extra GitHub calls needed. "Cycle time" here means open -> merged/closed,
not time-to-first-review — see
docs/architecture/0009-engineering-analytics.md for why that's the
metric this phase measures under the "PR review latency" heading."""

import statistics
from collections import defaultdict

from app.models.analytics_snapshot import PRCycleTimeSampleRecord
from app.models.pull_request import PullRequest


def bucket_daily_pr_counts(pull_requests: list[PullRequest]) -> dict[str, dict[str, int]]:
    """`{date: {"opened": n, "merged": n, "closed": n}}` — merged into the
    combined DailyPRIssueRecord list by the caller (analytics_service.py),
    which also has the issue-activity half."""
    buckets: dict[str, dict[str, int]] = defaultdict(
        lambda: {"opened": 0, "merged": 0, "closed": 0}
    )
    for pr in pull_requests:
        buckets[pr.github_created_at.date().isoformat()]["opened"] += 1
        if pr.merged_at:
            buckets[pr.merged_at.date().isoformat()]["merged"] += 1
        elif pr.closed_at:
            buckets[pr.closed_at.date().isoformat()]["closed"] += 1
    return dict(buckets)


def compute_cycle_time(
    pull_requests: list[PullRequest], *, limit: int
) -> tuple[float | None, list[PRCycleTimeSampleRecord]]:
    hours_by_pr: list[tuple[PullRequest, float]] = []
    for pr in pull_requests:
        end = pr.merged_at or pr.closed_at
        if end is None:
            continue
        hours_by_pr.append((pr, (end - pr.github_created_at).total_seconds() / 3600))

    if not hours_by_pr:
        return None, []

    median = statistics.median(hours for _pr, hours in hours_by_pr)
    slowest = sorted(hours_by_pr, key=lambda pair: pair[1], reverse=True)[:limit]
    samples = [
        PRCycleTimeSampleRecord(
            number=pr.number,
            title=pr.title,
            html_url=pr.html_url,
            hours=round(hours, 1),
            merged_at=pr.merged_at.isoformat() if pr.merged_at else None,
        )
        for pr, hours in slowest
    ]
    return median, samples
