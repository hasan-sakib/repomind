import uuid
from datetime import UTC, datetime

from app.analytics.pull_requests import bucket_daily_pr_counts, compute_cycle_time
from app.models.pull_request import PullRequest


def _pr(
    number: int,
    *,
    created: datetime,
    merged: datetime | None = None,
    closed: datetime | None = None,
) -> PullRequest:
    return PullRequest(
        id=uuid.uuid4(),
        repository_id=uuid.uuid4(),
        number=number,
        title=f"PR {number}",
        state="closed" if (merged or closed) else "open",
        author_login="ada",
        html_url=f"https://github.com/acme/widgets/pull/{number}",
        head_sha="f" * 40,
        github_created_at=created,
        github_updated_at=merged or closed or created,
        closed_at=closed,
        merged_at=merged,
        synced_at=created,
    )


def test_bucket_daily_pr_counts_tracks_opened_merged_closed_separately() -> None:
    prs = [
        _pr(1, created=datetime(2026, 1, 1, tzinfo=UTC), merged=datetime(2026, 1, 3, tzinfo=UTC)),
        _pr(2, created=datetime(2026, 1, 1, tzinfo=UTC), closed=datetime(2026, 1, 2, tzinfo=UTC)),
        _pr(3, created=datetime(2026, 1, 3, tzinfo=UTC)),
    ]
    buckets = bucket_daily_pr_counts(prs)
    assert buckets["2026-01-01"]["opened"] == 2
    assert buckets["2026-01-02"]["closed"] == 1
    assert buckets["2026-01-03"] == {"opened": 1, "merged": 1, "closed": 0}


def test_open_pr_with_no_merge_or_close_only_counts_as_opened() -> None:
    prs = [_pr(1, created=datetime(2026, 1, 1, tzinfo=UTC))]
    buckets = bucket_daily_pr_counts(prs)
    assert buckets == {"2026-01-01": {"opened": 1, "merged": 0, "closed": 0}}


def test_compute_cycle_time_ignores_still_open_prs() -> None:
    prs = [
        _pr(1, created=datetime(2026, 1, 1, tzinfo=UTC), merged=datetime(2026, 1, 2, tzinfo=UTC)),
        _pr(2, created=datetime(2026, 1, 1, tzinfo=UTC)),  # still open
    ]
    median, samples = compute_cycle_time(prs, limit=10)
    assert median == 24.0
    assert len(samples) == 1
    assert samples[0]["number"] == 1


def test_compute_cycle_time_median_of_multiple_samples() -> None:
    prs = [
        _pr(1, created=datetime(2026, 1, 1, tzinfo=UTC), merged=datetime(2026, 1, 2, tzinfo=UTC)),
        _pr(2, created=datetime(2026, 1, 1, tzinfo=UTC), merged=datetime(2026, 1, 4, tzinfo=UTC)),
        _pr(
            3, created=datetime(2026, 1, 1, tzinfo=UTC), merged=datetime(2026, 1, 1, 12, tzinfo=UTC)
        ),
    ]
    median, samples = compute_cycle_time(prs, limit=10)
    assert median == 24.0  # 12h, 24h, 72h -> median 24h
    assert [s["number"] for s in samples] == [2, 1, 3]  # slowest first


def test_compute_cycle_time_respects_limit() -> None:
    prs = [
        _pr(i, created=datetime(2026, 1, 1, tzinfo=UTC), merged=datetime(2026, 1, 2, tzinfo=UTC))
        for i in range(5)
    ]
    _, samples = compute_cycle_time(prs, limit=2)
    assert len(samples) == 2


def test_compute_cycle_time_with_no_resolved_prs_returns_none() -> None:
    median, samples = compute_cycle_time(
        [_pr(1, created=datetime(2026, 1, 1, tzinfo=UTC))], limit=10
    )
    assert median is None
    assert samples == []
