"""Thin wrapper around tree-sitter parsing. Nothing here inspects grammar
internals — that lives in chunker.py, which walks the returned Tree."""

from dataclasses import dataclass

from tree_sitter import Node, Parser, Tree

from app.indexing.languages import get_ts_language


@dataclass(frozen=True, slots=True)
class ParseResult:
    tree: Tree
    root: Node
    source: bytes
    has_errors: bool


def parse_source(source: bytes, language: str) -> ParseResult | None:
    """Parse `source` with the tree-sitter grammar for `language`, or return
    None if no grammar is registered for it (caller should fall back to
    prose chunking)."""
    ts_language = get_ts_language(language)
    if ts_language is None:
        return None
    parser = Parser(ts_language)
    tree = parser.parse(source)
    return ParseResult(
        tree=tree, root=tree.root_node, source=source, has_errors=tree.root_node.has_error
    )
