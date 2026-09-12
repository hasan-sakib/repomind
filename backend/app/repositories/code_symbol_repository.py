import uuid

from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code_symbol import CodeSymbol


def create(
    db: AsyncSession,
    *,
    file_id: uuid.UUID,
    symbol_type: str,
    name: str,
    start_line: int,
    end_line: int,
    signature: str | None,
    docstring: str | None,
    parent_symbol_id: uuid.UUID | None,
) -> CodeSymbol:
    symbol = CodeSymbol(
        file_id=file_id,
        symbol_type=symbol_type,
        name=name,
        start_line=start_line,
        end_line=end_line,
        signature=signature,
        docstring=docstring,
        parent_symbol_id=parent_symbol_id,
    )
    db.add(symbol)
    return symbol


async def delete_for_file(db: AsyncSession, file_id: uuid.UUID) -> None:
    await db.execute(sa_delete(CodeSymbol).where(CodeSymbol.file_id == file_id))
