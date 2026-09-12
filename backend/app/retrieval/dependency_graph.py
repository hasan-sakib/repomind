"""A lightweight, import-based dependency graph — not a full per-language
import resolver or call graph. "What depends on X" is answered by scanning
every file's recorded import statements (app/indexing/chunker.py) for a
word-boundary match on X's name; "what does X depend on" is answered by
the defining file's own import list. This is deliberately import-level,
not usage-level (a file that uses a symbol via `from x import *` or a
dynamically-resolved reference won't be found) — see
docs/architecture/0005-ai-rag-engine.md for the scope decision and why a
real resolver is future work, not a gap papered over here.
"""

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.chat_status import RetrievalSourceType
from app.domain.code_file import CodeFile
from app.domain.code_symbol import CodeSymbol
from app.retrieval.types import RetrievedChunk

# Symbol/class-like types preferred when several symbols share a name
# (e.g. a method and a class both called "Client") — a dependency query
# almost always means "the class/interface", not one of its methods.
_DEFINITION_PRIORITY = {
    "class": 0,
    "interface": 1,
    "type": 2,
    "struct": 3,
    "function": 4,
    "method": 5,
}


def _name_pattern(symbol_name: str) -> re.Pattern[str]:
    return re.compile(r"\b" + re.escape(symbol_name) + r"\b")


async def find_definition(
    db: AsyncSession, *, repository_id: uuid.UUID, symbol_name: str
) -> RetrievedChunk | None:
    result = await db.execute(
        select(CodeSymbol, CodeFile.path)
        .join(CodeFile, CodeSymbol.file_id == CodeFile.id)
        .where(CodeFile.repository_id == repository_id, CodeSymbol.name.ilike(symbol_name))
    )
    candidates = result.all()
    if not candidates:
        return None
    symbol, path = min(candidates, key=lambda row: _DEFINITION_PRIORITY.get(row[0].symbol_type, 9))

    content = symbol.signature or symbol.name
    if symbol.docstring:
        content = f"{content}\n{symbol.docstring}"
    return RetrievedChunk(
        source_type=RetrievalSourceType.DEPENDENCY,
        file_path=path,
        content=content,
        start_line=symbol.start_line,
        end_line=symbol.end_line,
        symbol_name=symbol.name,
        score=None,
    )


async def find_dependents(
    db: AsyncSession, *, repository_id: uuid.UUID, symbol_name: str, limit: int
) -> list[RetrievedChunk]:
    """Files that import something matching `symbol_name` by name."""
    pattern = _name_pattern(symbol_name)
    result = await db.execute(
        select(CodeFile.path, CodeFile.imports).where(CodeFile.repository_id == repository_id)
    )

    matches: list[RetrievedChunk] = []
    for path, imports in result.all():
        for record in imports:
            if pattern.search(record["text"]):
                matches.append(
                    RetrievedChunk(
                        source_type=RetrievalSourceType.DEPENDENCY,
                        file_path=path,
                        content=record["text"],
                        start_line=record["line"],
                        end_line=record["line"],
                        symbol_name=symbol_name,
                        score=None,
                    )
                )
                break  # one citation per file is enough
        if len(matches) >= limit:
            break
    return matches
