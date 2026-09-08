import uuid
from datetime import datetime

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.code_file import CodeFile


async def list_for_repository(db: AsyncSession, repository_id: uuid.UUID) -> list[CodeFile]:
    result = await db.execute(select(CodeFile).where(CodeFile.repository_id == repository_id))
    return list(result.scalars().all())


async def get_by_path(db: AsyncSession, *, repository_id: uuid.UUID, path: str) -> CodeFile | None:
    result = await db.execute(
        select(CodeFile).where(CodeFile.repository_id == repository_id, CodeFile.path == path)
    )
    return result.scalar_one_or_none()


def create(
    db: AsyncSession,
    *,
    repository_id: uuid.UUID,
    path: str,
    language: str | None,
    size_bytes: int,
    content_hash: str,
    commit_sha: str,
    imports: list[str],
    indexed_at: datetime,
) -> CodeFile:
    code_file = CodeFile(
        repository_id=repository_id,
        path=path,
        language=language,
        size_bytes=size_bytes,
        content_hash=content_hash,
        commit_sha=commit_sha,
        imports=imports,
        indexed_at=indexed_at,
    )
    db.add(code_file)
    return code_file


def update(
    code_file: CodeFile,
    *,
    language: str | None,
    size_bytes: int,
    content_hash: str,
    commit_sha: str,
    imports: list[str],
    indexed_at: datetime,
) -> None:
    code_file.language = language
    code_file.size_bytes = size_bytes
    code_file.content_hash = content_hash
    code_file.commit_sha = commit_sha
    code_file.imports = imports
    code_file.indexed_at = indexed_at


async def delete_missing(
    db: AsyncSession, *, repository_id: uuid.UUID, keep_paths: list[str]
) -> None:
    """Removes files that no longer exist in the repository (deleted or
    renamed since the last index)."""
    stmt = sa_delete(CodeFile).where(CodeFile.repository_id == repository_id)
    if keep_paths:
        stmt = stmt.where(CodeFile.path.notin_(keep_paths))
    await db.execute(stmt)
