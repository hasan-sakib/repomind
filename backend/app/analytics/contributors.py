"""Combines commit and PR authorship into one contributor leaderboard —
the "contributor activity" metric and the data behind the frontend's
contributor filter."""

from collections import defaultdict

from app.domain.analytics_snapshot import ContributorActivityRecord, DailyCommitRecord
from app.domain.pull_request import PullRequest


def build_contributor_activity(
    daily_commits: list[DailyCommitRecord], pull_requests: list[PullRequest]
) -> list[ContributorActivityRecord]:
    commit_counts: dict[str | None, int] = defaultdict(int)
    names: dict[str | None, str | None] = {}
    for record in daily_commits:
        commit_counts[record["login"]] += record["count"]
        if names.get(record["login"]) is None:
            names[record["login"]] = record["name"]

    pr_counts: dict[str | None, int] = defaultdict(int)
    for pr in pull_requests:
        pr_counts[pr.author_login] += 1

    logins = set(commit_counts) | set(pr_counts)
    return sorted(
        (
            ContributorActivityRecord(
                login=login,
                name=names.get(login),
                commit_count=commit_counts.get(login, 0),
                pr_count=pr_counts.get(login, 0),
            )
            for login in logins
        ),
        key=lambda r: r["commit_count"] + r["pr_count"],
        reverse=True,
    )
