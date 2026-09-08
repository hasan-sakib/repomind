"""AST-aware chunking: turns a parsed file into CodeSymbol/CodeChunk
candidates without ever falling back to a fixed-size character split.

Chunk boundaries always follow a structural boundary:
- grammar-backed languages: one chunk per function/method/interface/type
  declaration (a class with nested methods gets a small header-only chunk
  instead of one giant chunk duplicating its methods' content);
- everything else (Markdown, JSON, YAML, plain text, ...): heading/
  paragraph boundaries for Markdown, blank-line paragraph boundaries
  otherwise — see `_prose_chunks`. A line-count cap only decides where a
  chunk that is still too large gets split *between* lines, never inside
  one, and only after the structural split has already been applied.
"""

import hashlib
from dataclasses import dataclass

from tree_sitter import Node

from app.indexing.languages import LanguageConfig, get_language_config
from app.indexing.parser import ParseResult

# len(text) // 4 is the standard rough token-count heuristic for
# English-like text used when no tokenizer for the target embedding model
# is wired up; good enough to size chunks sensibly, not for billing.
_CHARS_PER_TOKEN = 4


def _text(node: Node) -> str:
    return (node.text or b"").decode("utf-8", errors="replace")


@dataclass(frozen=True, slots=True)
class ExtractedSymbol:
    symbol_type: str
    name: str
    start_line: int
    end_line: int
    signature: str | None
    docstring: str | None
    parent_index: int | None


@dataclass(frozen=True, slots=True)
class ExtractedChunk:
    chunk_type: str
    content: str
    start_line: int
    end_line: int
    content_hash: str
    token_count: int
    symbol_index: int | None


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    symbols: list[ExtractedSymbol]
    chunks: list[ExtractedChunk]
    imports: list[str]


def _make_chunk(
    chunk_type: str, content: str, start_line: int, end_line: int, symbol_index: int | None
) -> ExtractedChunk:
    content = content.strip("\n")
    return ExtractedChunk(
        chunk_type=chunk_type,
        content=content,
        start_line=start_line,
        end_line=end_line,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        token_count=max(1, len(content) // _CHARS_PER_TOKEN),
        symbol_index=symbol_index,
    )


def _clean_comment(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        for marker in ("/**", "/*", "*/", "*", "///", "//"):
            if line.startswith(marker):
                line = line[len(marker) :].strip()
                break
        lines.append(line)
    return "\n".join(lines).strip()


def _leading_comment(node: Node) -> str | None:
    parent = node.parent
    if parent is None:
        return None
    siblings = parent.children
    try:
        index = siblings.index(node)
    except ValueError:
        return None
    if index == 0:
        return None
    previous = siblings[index - 1]
    if previous.type != "comment":
        return None
    cleaned = _clean_comment(_text(previous))
    return cleaned or None


def _python_docstring(node: Node, source: bytes) -> str | None:
    body = node.child_by_field_name("body")
    if body is None or body.named_child_count == 0:
        return None
    first = body.named_children[0]
    if first.type != "expression_statement" or first.named_child_count == 0:
        return None
    string_node = first.named_children[0]
    if string_node.type != "string":
        return None
    raw = _text(string_node).strip()
    for quote in ('"""', "'''", '"', "'"):
        if raw.startswith(quote) and raw.endswith(quote) and len(raw) >= 2 * len(quote):
            return raw[len(quote) : -len(quote)].strip()
    return raw


def _extract_docstring(node: Node, language: str, source: bytes) -> str | None:
    if language == "python":
        return _python_docstring(node, source)
    return _leading_comment(node)


def _signature(node: Node) -> str:
    first_line = _text(node).splitlines()[0]
    return first_line.strip()


def _walk(
    node: Node,
    config: LanguageConfig,
    source: bytes,
    language: str,
    symbols: list[ExtractedSymbol],
    chunks: list[ExtractedChunk],
    imports: list[str],
    parent_index: int | None,
    ancestor_is_class: bool,
) -> None:
    for child in node.named_children:
        if child.type in config.import_nodes:
            imports.append(_text(child).strip())
            continue

        if child.type not in config.symbol_nodes:
            _walk(
                child,
                config,
                source,
                language,
                symbols,
                chunks,
                imports,
                parent_index,
                ancestor_is_class,
            )
            continue

        symbol_type = config.symbol_nodes[child.type]
        if symbol_type == "function" and ancestor_is_class:
            symbol_type = "method"

        name_node = child.child_by_field_name("name")
        name = _text(name_node) if name_node else "<anonymous>"
        start_line = child.start_point[0] + 1
        end_line = child.end_point[0] + 1

        symbol_index = len(symbols)
        symbols.append(
            ExtractedSymbol(
                symbol_type=symbol_type,
                name=name,
                start_line=start_line,
                end_line=end_line,
                signature=_signature(child),
                docstring=_extract_docstring(child, language, source),
                parent_index=parent_index,
            )
        )

        is_container = child.type in config.class_nodes
        nested_symbols_before = len(symbols)
        nested_chunks_before = len(chunks)
        _walk(
            child,
            config,
            source,
            language,
            symbols,
            chunks,
            imports,
            symbol_index,
            ancestor_is_class=is_container,
        )
        has_nested_symbols = len(symbols) > nested_symbols_before

        if is_container and has_nested_symbols:
            # A header-only chunk (docstring + class-level attributes),
            # excluding nested method bodies — those already got their own
            # chunks above, via the recursive _walk call.
            first_nested = symbols[nested_symbols_before]
            header_end_line = max(start_line, first_nested.start_line - 1)
            header_text = b"\n".join(source.splitlines()[start_line - 1 : header_end_line])
            if header_text.strip():
                chunks.insert(
                    nested_chunks_before,
                    _make_chunk(
                        symbol_type,
                        header_text.decode("utf-8", errors="replace"),
                        start_line,
                        header_end_line,
                        symbol_index,
                    ),
                )
        else:
            chunks.append(
                _make_chunk(
                    symbol_type,
                    _text(child),
                    start_line,
                    end_line,
                    symbol_index,
                )
            )


def _prose_chunks(text: str, max_chunk_lines: int) -> list[ExtractedChunk]:
    lines = text.splitlines()
    if not lines:
        return []

    # Section boundaries: Markdown headings if present, else paragraph
    # breaks (blank lines) — both are structural, not arbitrary offsets.
    section_starts = [i for i, line in enumerate(lines) if line.startswith("#")]
    if not section_starts:
        section_starts = [0] + [i + 1 for i, line in enumerate(lines) if line.strip() == ""]
    section_starts = sorted(set(section_starts) | {0})

    sections: list[tuple[int, int]] = []
    for i, start in enumerate(section_starts):
        end = section_starts[i + 1] if i + 1 < len(section_starts) else len(lines)
        if end > start:
            sections.append((start, end))

    chunks: list[ExtractedChunk] = []
    for start, end in sections:
        for sub_start in range(start, end, max_chunk_lines):
            sub_end = min(sub_start + max_chunk_lines, end)
            content = "\n".join(lines[sub_start:sub_end])
            if content.strip():
                chunks.append(_make_chunk("prose", content, sub_start + 1, sub_end, None))
    return chunks


def extract(
    parse_result: ParseResult | None,
    source_text: str,
    language: str | None,
    *,
    max_chunk_lines: int,
) -> ExtractionResult:
    if language is None:
        return ExtractionResult(
            symbols=[], chunks=_prose_chunks(source_text, max_chunk_lines), imports=[]
        )
    config = get_language_config(language)
    if parse_result is None or config is None:
        return ExtractionResult(
            symbols=[], chunks=_prose_chunks(source_text, max_chunk_lines), imports=[]
        )

    symbols: list[ExtractedSymbol] = []
    chunks: list[ExtractedChunk] = []
    imports: list[str] = []
    _walk(
        parse_result.root,
        config,
        parse_result.source,
        language,
        symbols,
        chunks,
        imports,
        parent_index=None,
        ancestor_is_class=False,
    )

    # A file with no extracted symbols at all (e.g. a script with only
    # top-level statements) still gets indexed via the prose fallback so
    # its content remains searchable.
    if not chunks:
        chunks = _prose_chunks(source_text, max_chunk_lines)

    return ExtractionResult(symbols=symbols, chunks=chunks, imports=imports)
