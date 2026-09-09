"""Orchestrates one indexing run end to end: GitHub Repository ->
Repository Fetcher -> File Discovery -> File Filtering -> Language
Detection -> Tree-sitter Parsing -> AST-aware Chunking -> Metadata
Extraction -> Embedding Generation -> PostgreSQL + pgvector.

Progress fields on the IndexingJob row are committed incrementally — after
every file, and after every embedding batch — not just once at the end, so
a client polling GET /repositories/{id}/indexing-jobs/{job_id} sees
genuine progress rather than a job that jumps straight from "queued" to
"succeeded"; see docs/architecture/0004-codebase-indexing.md.
"""

import hashlib
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.embedding_provider import EmbeddingProvider
from app.core.config import Settings, get_settings
from app.domain.code_file import ImportRecord
from app.domain.indexing_job import IndexingJob
from app.domain.indexing_status import IndexingJobStatus, IndexingStage
from app.domain.repository import Repository
from app.events.publish import publish_notification, publish_state
from app.events.types import EventCategory
from app.indexing import chunker, discovery
from app.indexing.parser import parse_source
from app.integrations.git.fetcher import clone_repository
from app.repositories import (
    code_chunk_repository,
    code_embedding_repository,
    code_file_repository,
    code_symbol_repository,
    indexing_error_repository,
    indexing_job_repository,
)
from app.schemas.indexing import IndexingJobPublic

logger = logging.getLogger("repomind.indexing")

# voyageai.VOYAGE_EMBED_BATCH_SIZE is 128 — batching this many chunks per
# embed() call keeps requests well inside that limit.
_EMBEDDING_BATCH_SIZE = 128


async def _persist(db: AsyncSession, job: IndexingJob, repository: Repository) -> None:
    """Commits the job's current progress and pushes the same state onto
    this repository's real-time channel — one choke point rather than a
    publish call duplicated at every one of update_progress's call sites.
    See docs/architecture/0010-realtime-infrastructure.md."""
    await db.commit()
    await publish_state(
        category=EventCategory.INDEXING,
        organization_id=repository.organization_id,
        repository_id=repository.id,
        resource="indexing_job",
        data=IndexingJobPublic.from_job(job).model_dump(mode="json"),
    )


async def run_indexing_job(
    db: AsyncSession, job: IndexingJob, embedding_provider: EmbeddingProvider
) -> None:
    settings = get_settings()
    repository = await db.get(
        Repository, job.repository_id, options=[selectinload(Repository.installation)]
    )
    if repository is None:
        logger.warning(
            "Repository %s no longer exists; abandoning job %s", job.repository_id, job.id
        )
        indexing_job_repository.mark_finished(
            job,
            status=IndexingJobStatus.FAILED,
            finished_at=datetime.now(UTC),
            error="Repository no longer exists",
        )
        await db.commit()
        return

    indexing_job_repository.mark_running(job, started_at=datetime.now(UTC))
    await _persist(db, job, repository)

    try:
        had_errors, pending_embeddings = await _discover_and_chunk(db, job, repository, settings)

        indexing_job_repository.update_progress(job, current_stage=IndexingStage.EMBEDDING)
        await _persist(db, job, repository)
        had_embedding_errors = await _generate_embeddings(
            db, job, repository, pending_embeddings, embedding_provider
        )

        final_status = (
            IndexingJobStatus.PARTIAL
            if (had_errors or had_embedding_errors)
            else IndexingJobStatus.SUCCEEDED
        )
        indexing_job_repository.mark_finished(
            job, status=final_status, finished_at=datetime.now(UTC)
        )
        await _persist(db, job, repository)
        succeeded = final_status == IndexingJobStatus.SUCCEEDED
        outcome = "finished" if succeeded else "finished with some errors"
        await publish_notification(
            organization_id=repository.organization_id,
            repository_id=repository.id,
            title=f"Indexing {outcome} for {repository.full_name}",
            level="success" if succeeded else "error",
        )
    except Exception as exc:  # noqa: BLE001 — must never crash the worker task silently
        logger.exception("Indexing job %s failed", job.id)
        await db.rollback()
        indexing_job_repository.mark_finished(
            job, status=IndexingJobStatus.FAILED, finished_at=datetime.now(UTC), error=str(exc)
        )
        await _persist(db, job, repository)
        await publish_notification(
            organization_id=repository.organization_id,
            repository_id=repository.id,
            title=f"Indexing failed for {repository.full_name}",
            level="error",
        )


async def _discover_and_chunk(
    db: AsyncSession, job: IndexingJob, repository: Repository, settings: Settings
) -> tuple[bool, list[tuple[uuid.UUID, str]]]:
    """Clones the repo, discovers/filters/parses/chunks every file, and
    writes CodeFile/CodeSymbol/CodeChunk rows. Returns (had_errors, pending
    embeddings) — chunk id/content pairs still needing a vector, produced
    after the clone's temp directory (no longer needed past this point) is
    cleaned up."""
    had_errors = False
    kept_paths: list[str] = []
    pending_embeddings: list[tuple[uuid.UUID, str]] = []
    files_processed = 0
    files_skipped = 0
    symbols_extracted = 0
    chunks_created = 0

    indexing_job_repository.update_progress(job, current_stage=IndexingStage.FETCHING)
    await _persist(db, job, repository)

    async with clone_repository(
        installation_id=repository.installation.github_installation_id,
        full_name=repository.full_name,
        commit_sha=job.commit_sha,
    ) as repo_root:
        indexing_job_repository.update_progress(job, current_stage=IndexingStage.DISCOVERING)
        await _persist(db, job, repository)

        discovered = discovery.discover_files(
            repo_root,
            max_file_size_bytes=settings.indexing_max_file_size_bytes,
            max_files=settings.indexing_max_files_per_repository,
        )
        indexing_job_repository.update_progress(
            job, current_stage=IndexingStage.FILTERING, files_discovered=len(discovered)
        )
        await _persist(db, job, repository)

        for file in discovered:
            kept_paths.append(file.path)
            try:
                content_bytes = file.absolute_path.read_bytes()
            except OSError as exc:
                had_errors = True
                indexing_error_repository.create(
                    db,
                    job_id=job.id,
                    file_path=file.path,
                    stage=IndexingStage.DISCOVERING,
                    message=str(exc),
                )
                continue

            content_hash = hashlib.sha256(content_bytes).hexdigest()
            existing = await code_file_repository.get_by_path(
                db, repository_id=repository.id, path=file.path
            )
            if existing is not None and existing.content_hash == content_hash:
                files_skipped += 1
                indexing_job_repository.update_progress(
                    job, current_stage=IndexingStage.FILTERING, files_skipped=files_skipped
                )
                await _persist(db, job, repository)
                continue

            try:
                indexing_job_repository.update_progress(job, current_stage=IndexingStage.PARSING)
                parse_result = parse_source(content_bytes, file.language) if file.language else None

                indexing_job_repository.update_progress(job, current_stage=IndexingStage.CHUNKING)
                extraction = chunker.extract(
                    parse_result,
                    content_bytes.decode("utf-8", errors="replace"),
                    file.language,
                    max_chunk_lines=settings.indexing_max_chunk_lines,
                )
            except Exception as exc:  # noqa: BLE001 — one bad file must not fail the whole job
                had_errors = True
                indexing_error_repository.create(
                    db,
                    job_id=job.id,
                    file_path=file.path,
                    stage=IndexingStage.PARSING,
                    message=str(exc),
                )
                continue

            import_records: list[ImportRecord] = [
                {"text": imp.text, "line": imp.line} for imp in extraction.imports
            ]
            if existing is not None:
                await code_symbol_repository.delete_for_file(db, existing.id)
                await code_chunk_repository.delete_for_file(db, existing.id)
                code_file_repository.update(
                    existing,
                    language=file.language,
                    size_bytes=file.size_bytes,
                    content_hash=content_hash,
                    commit_sha=job.commit_sha,
                    imports=import_records,
                    indexed_at=datetime.now(UTC),
                )
                code_file = existing
            else:
                code_file = code_file_repository.create(
                    db,
                    repository_id=repository.id,
                    path=file.path,
                    language=file.language,
                    size_bytes=file.size_bytes,
                    content_hash=content_hash,
                    commit_sha=job.commit_sha,
                    imports=import_records,
                    indexed_at=datetime.now(UTC),
                )
            await db.flush()

            created_symbol_ids: list[uuid.UUID] = []
            for symbol in extraction.symbols:
                parent_id = (
                    created_symbol_ids[symbol.parent_index]
                    if symbol.parent_index is not None
                    else None
                )
                row = code_symbol_repository.create(
                    db,
                    file_id=code_file.id,
                    symbol_type=symbol.symbol_type,
                    name=symbol.name,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    signature=symbol.signature,
                    docstring=symbol.docstring,
                    parent_symbol_id=parent_id,
                )
                await db.flush()
                created_symbol_ids.append(row.id)
            symbols_extracted += len(created_symbol_ids)

            for extracted_chunk in extraction.chunks:
                symbol_id = (
                    created_symbol_ids[extracted_chunk.symbol_index]
                    if extracted_chunk.symbol_index is not None
                    else None
                )
                chunk_row = code_chunk_repository.create(
                    db,
                    file_id=code_file.id,
                    symbol_id=symbol_id,
                    chunk_type=extracted_chunk.chunk_type,
                    content=extracted_chunk.content,
                    start_line=extracted_chunk.start_line,
                    end_line=extracted_chunk.end_line,
                    content_hash=extracted_chunk.content_hash,
                    token_count=extracted_chunk.token_count,
                )
                await db.flush()
                pending_embeddings.append((chunk_row.id, extracted_chunk.content))
            chunks_created += len(extraction.chunks)

            files_processed += 1
            indexing_job_repository.update_progress(
                job,
                current_stage=IndexingStage.CHUNKING,
                files_processed=files_processed,
                files_skipped=files_skipped,
                symbols_extracted=symbols_extracted,
                chunks_created=chunks_created,
            )
            await _persist(db, job, repository)

        await code_file_repository.delete_missing(
            db, repository_id=repository.id, keep_paths=kept_paths
        )
        await db.commit()

    return had_errors, pending_embeddings


async def _generate_embeddings(
    db: AsyncSession,
    job: IndexingJob,
    repository: Repository,
    pending_embeddings: list[tuple[uuid.UUID, str]],
    embedding_provider: EmbeddingProvider,
) -> bool:
    had_errors = False
    embeddings_generated = 0

    for batch_start in range(0, len(pending_embeddings), _EMBEDDING_BATCH_SIZE):
        batch = pending_embeddings[batch_start : batch_start + _EMBEDDING_BATCH_SIZE]
        try:
            result = await embedding_provider.embed(
                [text for _, text in batch], input_type="document"
            )
        except Exception as exc:  # noqa: BLE001 — a batch failure shouldn't drop indexed structure
            had_errors = True
            indexing_error_repository.create(
                db, job_id=job.id, file_path=None, stage=IndexingStage.EMBEDDING, message=str(exc)
            )
            await db.commit()
            break

        for (chunk_id, _), vector in zip(batch, result.vectors, strict=True):
            code_embedding_repository.create(
                db, chunk_id=chunk_id, embedding=vector, model=result.model
            )
        embeddings_generated += len(batch)
        indexing_job_repository.update_progress(
            job, current_stage=IndexingStage.EMBEDDING, embeddings_generated=embeddings_generated
        )
        await _persist(db, job, repository)

    return had_errors
