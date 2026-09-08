"""Shallow-clones a connected repository at a specific commit so the
indexing pipeline can walk its working tree. Authenticates with a
fresh GitHub App installation token (app_client.get_installation_access_token)
embedded in the clone URL — never written to disk or logged."""

import asyncio
import shutil
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from app.integrations.github.app_client import get_installation_access_token


class GitFetchError(Exception):
    """Raised when cloning or checking out a repository fails."""


def _redact(text: str, token: str) -> str:
    return text.replace(token, "***") if token else text


async def _run_git(args: list[str], *, token: str, cwd: Path | None = None) -> None:
    process = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        message = _redact(stderr.decode("utf-8", errors="replace"), token)
        raise GitFetchError(f"git {args[0]} failed: {message}")


@asynccontextmanager
async def clone_repository(
    *, installation_id: int, full_name: str, commit_sha: str
) -> AsyncIterator[Path]:
    """Shallow-clone `full_name` and check out `commit_sha`, yielding the
    working tree's path. Always cleans up the temp directory, including on
    failure — the caller never has to remember to."""
    token = await get_installation_access_token(installation_id)
    url = f"https://x-access-token:{token}@github.com/{full_name}.git"
    tmp_dir = Path(tempfile.mkdtemp(prefix="repomind-clone-"))
    try:
        await _run_git(
            ["clone", "--depth", "1", "--single-branch", "--no-tags", url, str(tmp_dir)],
            token=token,
        )
        # The initial shallow clone only has the default branch's tip.
        # Fetching by exact SHA (GitHub supports this) covers re-index and
        # webhook-triggered jobs targeting a different commit.
        await _run_git(["fetch", "--depth", "1", "origin", commit_sha], token=token, cwd=tmp_dir)
        await _run_git(["checkout", "FETCH_HEAD"], token=token, cwd=tmp_dir)
        yield tmp_dir
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
