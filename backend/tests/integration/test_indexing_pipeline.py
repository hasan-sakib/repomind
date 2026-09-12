import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedding_provider import EmbeddingProvider, EmbeddingResult
from app.db.session import async_session_factory
from app.indexing import pipeline as pipeline_module
from app.models.code_chunk import CodeChunk
from app.models.code_embedding import CodeEmbedding
from app.models.code_file import CodeFile
from app.models.code_symbol import CodeSymbol
from app.models.indexing_job import IndexingJob
from app.models.indexing_status import IndexingJobStatus, IndexingStage, IndexingTrigger
from app.models.repository import Repository
from app.repositories import (
    branch_repository,
    github_installation_repository,
    indexing_job_repository,
    organization_repository,
    repository_repository,
)
from app.services import indexing_service

pytestmark = pytest.mark.asyncio


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str], *, input_type: str) -> EmbeddingResult:
        self.calls.append(list(texts))
        return EmbeddingResult(
            vectors=[[0.1] * 1024 for _ in texts],
            model="fake-embed-v1",
            total_tokens=len(texts) * 10,
        )


async def _create_repository(db: AsyncSession, *, default_branch_sha: str = "a" * 40) -> Repository:
    organization = organization_repository.create(
        db, name="Acme", slug=f"acme-{uuid.uuid4().hex[:8]}"
    )
    await db.flush()

    installation = github_installation_repository.create(
        db,
        organization_id=organization.id,
        github_installation_id=1234,
        account_login="acme",
        account_type="Organization",
    )
    await db.flush()

    repository = repository_repository.create(
        db,
        organization_id=organization.id,
        installation_id=installation.id,
        github_repo_id=555,
        full_name="acme/widgets",
        name="widgets",
        description=None,
        language="Python",
        stargazers_count=0,
        forks_count=0,
        default_branch="main",
        private=False,
        html_url="https://github.com/acme/widgets",
    )
    await db.flush()

    branch_repository.create(
        db, repository_id=repository.id, name="main", commit_sha=default_branch_sha, is_default=True
    )
    await db.commit()
    return repository


def _fake_clone_factory(repo_dir: Path):
    @asynccontextmanager
    async def _fake_clone(*, installation_id: int, full_name: str, commit_sha: str):
        yield repo_dir

    return _fake_clone


async def _run_job(job_id: uuid.UUID, embedding_provider: EmbeddingProvider) -> None:
    """Runs the pipeline in a *fresh* session, exactly like the real
    `index_repository` arq task (app/workers/tasks.py) — never the caller's
    own session. Reusing the caller's session would leave the Repository
    already in its identity map without `.installation` eager-loaded,
    masking a lazy-load-in-async-context bug this test would otherwise
    hide."""
    async with async_session_factory() as db:
        job = await indexing_job_repository.get(db, job_id)
        assert job is not None
        await pipeline_module.run_indexing_job(db, job, embedding_provider)


async def test_trigger_indexing_prevents_duplicate_active_jobs(db_session: AsyncSession) -> None:
    repository = await _create_repository(db_session)

    first_job, first_started = await indexing_service.trigger_indexing(
        db_session, repository=repository, trigger=IndexingTrigger.MANUAL
    )
    assert first_started is True
    assert first_job.status == IndexingJobStatus.QUEUED

    second_job, second_started = await indexing_service.trigger_indexing(
        db_session, repository=repository, trigger=IndexingTrigger.MANUAL
    )

    assert second_started is False
    assert second_job.id == first_job.id

    active_count = await db_session.execute(
        select(IndexingJob).where(IndexingJob.repository_id == repository.id)
    )
    assert len(active_count.scalars().all()) == 1


async def test_run_indexing_job_extracts_symbols_chunks_and_embeddings(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = await _create_repository(db_session)
    (tmp_path / "app.py").write_text(
        'def add(a, b):\n    """Add two numbers."""\n    return a + b\n'
    )
    (tmp_path / "README.md").write_text("# Widgets\n\nA widget factory.\n")

    monkeypatch.setattr(pipeline_module, "clone_repository", _fake_clone_factory(tmp_path))

    job = indexing_job_repository.create(
        db_session,
        repository_id=repository.id,
        trigger=IndexingTrigger.INITIAL,
        commit_sha="a" * 40,
    )
    await db_session.commit()

    embedding_provider = FakeEmbeddingProvider()
    await _run_job(job.id, embedding_provider)
    await db_session.refresh(job)

    assert job.status == IndexingJobStatus.SUCCEEDED
    assert job.current_stage == IndexingStage.DONE
    assert job.files_processed == 2
    assert job.files_skipped == 0
    assert job.symbols_extracted == 1
    assert job.chunks_created >= 2
    assert job.embeddings_generated == job.chunks_created
    assert embedding_provider.calls  # the pipeline actually called embed()

    files = (
        (await db_session.execute(select(CodeFile).where(CodeFile.repository_id == repository.id)))
        .scalars()
        .all()
    )
    assert {f.path for f in files} == {"app.py", "README.md"}

    symbols = (await db_session.execute(select(CodeSymbol))).scalars().all()
    assert [s.name for s in symbols] == ["add"]
    assert symbols[0].docstring == "Add two numbers."

    chunks = (await db_session.execute(select(CodeChunk))).scalars().all()
    embeddings = (await db_session.execute(select(CodeEmbedding))).scalars().all()
    assert len(embeddings) == len(chunks)


async def test_run_indexing_job_skips_unchanged_files_on_rerun(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = await _create_repository(db_session)
    (tmp_path / "app.py").write_text("def add(a, b):\n    return a + b\n")

    monkeypatch.setattr(pipeline_module, "clone_repository", _fake_clone_factory(tmp_path))

    first_job = indexing_job_repository.create(
        db_session,
        repository_id=repository.id,
        trigger=IndexingTrigger.INITIAL,
        commit_sha="a" * 40,
    )
    await db_session.commit()
    await _run_job(first_job.id, FakeEmbeddingProvider())
    await db_session.refresh(first_job)
    assert first_job.files_processed == 1
    assert first_job.files_skipped == 0

    second_job = indexing_job_repository.create(
        db_session, repository_id=repository.id, trigger=IndexingTrigger.MANUAL, commit_sha="a" * 40
    )
    await db_session.commit()
    await _run_job(second_job.id, FakeEmbeddingProvider())
    await db_session.refresh(second_job)

    assert second_job.status == IndexingJobStatus.SUCCEEDED
    assert second_job.files_processed == 0
    assert second_job.files_skipped == 1

    # No duplicate CodeFile rows were created for the unchanged file.
    files = (
        (await db_session.execute(select(CodeFile).where(CodeFile.repository_id == repository.id)))
        .scalars()
        .all()
    )
    assert len(files) == 1
