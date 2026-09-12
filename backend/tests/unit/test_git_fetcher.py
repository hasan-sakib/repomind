import pytest

from app.integrations.git.fetcher import GitFetchError, clone_repository


async def test_invalid_full_name_is_rejected_before_any_network_call() -> None:
    with pytest.raises(GitFetchError, match="invalid repository name"):
        async with clone_repository(
            installation_id=1, full_name="--upload-pack=evil", commit_sha="a" * 40
        ):
            pass


async def test_invalid_commit_sha_is_rejected_before_any_network_call() -> None:
    with pytest.raises(GitFetchError, match="invalid commit sha"):
        async with clone_repository(
            installation_id=1, full_name="owner/repo", commit_sha="--upload-pack=evil"
        ):
            pass


async def test_valid_shape_passes_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Doesn't actually clone anything — just proves well-formed input gets
    past the validation added for security and reaches the (mocked) token
    fetch, i.e. the regexes aren't accidentally rejecting real input."""
    import app.integrations.git.fetcher as fetcher_module

    called = {}

    async def fake_get_token(installation_id: int) -> str:
        called["installation_id"] = installation_id
        raise RuntimeError("stop here — this test only cares that we got this far")

    monkeypatch.setattr(fetcher_module, "get_installation_access_token", fake_get_token)

    with pytest.raises(RuntimeError, match="stop here"):
        async with fetcher_module.clone_repository(
            installation_id=42, full_name="owner/repo.name-1", commit_sha="a" * 40
        ):
            pass

    assert called["installation_id"] == 42
