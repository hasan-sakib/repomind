from app.analytics.hotspots import aggregate_hotspots
from app.integrations.github.schemas import GitHubPullRequestFile


def _file(filename: str) -> GitHubPullRequestFile:
    return GitHubPullRequestFile(
        filename=filename, status="modified", additions=1, deletions=1, changes=2, patch=None
    )


def test_counts_changes_per_file_across_commits() -> None:
    commit_files = [
        [_file("app/services/auth_service.py"), _file("app/api/routes/auth.py")],
        [_file("app/services/auth_service.py")],
        [_file("app/services/auth_service.py")],
    ]

    file_hotspots, _ = aggregate_hotspots(commit_files, dependents_by_path={}, limit=10)

    by_path = {h["path"]: h["change_count"] for h in file_hotspots}
    assert by_path["app/services/auth_service.py"] == 3
    assert by_path["app/api/routes/auth.py"] == 1


def test_file_hotspots_sorted_descending_by_change_count() -> None:
    commit_files = [[_file("a.py")], [_file("a.py")], [_file("b.py")]]
    file_hotspots, _ = aggregate_hotspots(commit_files, dependents_by_path={}, limit=10)
    assert [h["path"] for h in file_hotspots] == ["a.py", "b.py"]


def test_file_hotspots_respect_limit() -> None:
    commit_files = [[_file("a.py")], [_file("b.py")], [_file("c.py")]]
    file_hotspots, _ = aggregate_hotspots(commit_files, dependents_by_path={}, limit=2)
    assert len(file_hotspots) == 2


def test_dependents_count_is_attached_from_the_provided_map() -> None:
    commit_files = [[_file("app/services/auth_service.py")]]
    file_hotspots, _ = aggregate_hotspots(
        commit_files, dependents_by_path={"app/services/auth_service.py": 4}, limit=10
    )
    assert file_hotspots[0]["dependents_count"] == 4


def test_unlisted_file_defaults_to_zero_dependents() -> None:
    commit_files = [[_file("app/services/auth_service.py")]]
    file_hotspots, _ = aggregate_hotspots(commit_files, dependents_by_path={}, limit=10)
    assert file_hotspots[0]["dependents_count"] == 0


def test_architecture_hotspots_roll_up_by_package_using_full_data_not_truncated_files() -> None:
    # Three files in the same package, each changed once — the package
    # rollup must reflect all three even though the file-level limit=1
    # only keeps one of them.
    commit_files = [
        [_file("app/services/auth_service.py")],
        [_file("app/services/billing_service.py")],
        [_file("app/services/email_service.py")],
    ]
    file_hotspots, architecture_hotspots = aggregate_hotspots(
        commit_files, dependents_by_path={}, limit=1
    )

    assert len(file_hotspots) == 1
    services_pkg = next(a for a in architecture_hotspots if a["package_path"] == "app/services")
    assert services_pkg["change_count"] == 3
    assert services_pkg["file_count"] == 3


def test_architecture_hotspots_classify_package_kind() -> None:
    commit_files = [[_file("app/repositories/user_repository.py")]]
    _, architecture_hotspots = aggregate_hotspots(commit_files, dependents_by_path={}, limit=10)
    assert architecture_hotspots[0]["kind"] == "repository"


def test_empty_input_yields_empty_hotspots() -> None:
    file_hotspots, architecture_hotspots = aggregate_hotspots([], dependents_by_path={}, limit=10)
    assert file_hotspots == []
    assert architecture_hotspots == []
