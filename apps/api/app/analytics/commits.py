"""Commit-activity aggregation — a deeper (still bounded) commit history
than the dashboard's 50-commit window, bucketed by day and author for the
commit-frequency and contributor-activity views."""

from collections import defaultdict

from app.domain.analytics_snapshot import DailyCommitRecord
from app.integrations.github.schemas import GitHubCommit


def bucket_daily_commits(commits: list[GitHubCommit]) -> list[DailyCommitRecord]:
    counts: dict[tuple[str, str | None], int] = defaultdict(int)
    names: dict[str | None, str | None] = {}
    for commit in commits:
        date = commit.authored_at.date().isoformat()
        counts[(date, commit.author_login)] += 1
        if names.get(commit.author_login) is None:
            names[commit.author_login] = commit.author_name

    return [
        DailyCommitRecord(date=date, login=login, name=names.get(login), count=count)
        for (date, login), count in sorted(counts.items())
    ]
