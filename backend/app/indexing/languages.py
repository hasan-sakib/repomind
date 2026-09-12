"""Extension -> language mapping and the tree-sitter grammar registry.

Only languages with a registered grammar get AST-aware parsing (symbols,
docstrings, imports). Every other recognized text file still gets indexed —
app/indexing/chunker.py falls back to prose chunking for it — but it is
never blindly split by raw character count; see chunker.py.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

import tree_sitter_go
import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_typescript
from tree_sitter import Language

# Node types that declare a named symbol, mapped to the label stored in
# CodeSymbol.symbol_type. A function_definition/function_declaration nested
# inside a class body is reclassified "method" at extraction time (see
# chunker.py) — grammars that already distinguish methods at the grammar
# level (method_definition, method_declaration) don't need that step.
_PYTHON_SYMBOL_NODES = {"function_definition": "function", "class_definition": "class"}
_JS_SYMBOL_NODES = {
    "function_declaration": "function",
    "class_declaration": "class",
    "method_definition": "method",
}
_TS_SYMBOL_NODES = _JS_SYMBOL_NODES | {
    "interface_declaration": "interface",
    "type_alias_declaration": "type",
}
_GO_SYMBOL_NODES = {
    "function_declaration": "function",
    "method_declaration": "method",
    "type_declaration": "type",
}

_PYTHON_IMPORT_NODES = {"import_statement", "import_from_statement"}
_JS_IMPORT_NODES = {"import_statement"}
_GO_IMPORT_NODES = {"import_declaration"}


@dataclass(frozen=True, slots=True)
class LanguageConfig:
    name: str
    grammar: Callable[[], object]
    symbol_nodes: dict[str, str]
    import_nodes: set[str]
    class_nodes: set[str]


_CONFIGS: dict[str, LanguageConfig] = {
    "python": LanguageConfig(
        name="python",
        grammar=tree_sitter_python.language,
        symbol_nodes=_PYTHON_SYMBOL_NODES,
        import_nodes=_PYTHON_IMPORT_NODES,
        class_nodes={"class_definition"},
    ),
    "javascript": LanguageConfig(
        name="javascript",
        grammar=tree_sitter_javascript.language,
        symbol_nodes=_JS_SYMBOL_NODES,
        import_nodes=_JS_IMPORT_NODES,
        class_nodes={"class_declaration"},
    ),
    "typescript": LanguageConfig(
        name="typescript",
        grammar=tree_sitter_typescript.language_typescript,
        symbol_nodes=_TS_SYMBOL_NODES,
        import_nodes=_JS_IMPORT_NODES,
        class_nodes={"class_declaration"},
    ),
    "tsx": LanguageConfig(
        name="tsx",
        grammar=tree_sitter_typescript.language_tsx,
        symbol_nodes=_TS_SYMBOL_NODES,
        import_nodes=_JS_IMPORT_NODES,
        class_nodes={"class_declaration"},
    ),
    "go": LanguageConfig(
        name="go",
        grammar=tree_sitter_go.language,
        symbol_nodes=_GO_SYMBOL_NODES,
        import_nodes=_GO_IMPORT_NODES,
        class_nodes=set(),
    ),
}

# Extensions recognized as source code with no tree-sitter grammar wired up
# yet still get discovered and indexed, just via the prose fallback chunker.
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".mts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".md": "markdown",
    ".mdx": "markdown",
    ".rst": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sql": "sql",
    ".sh": "shell",
    ".css": "css",
    ".html": "html",
}


def detect_language(path: str) -> str | None:
    for ext, language in EXTENSION_TO_LANGUAGE.items():
        if path.endswith(ext):
            return language
    return None


@lru_cache
def get_language_config(language: str) -> LanguageConfig | None:
    return _CONFIGS.get(language)


@lru_cache
def _get_ts_language(language: str) -> Language:
    return Language(_CONFIGS[language].grammar())


def get_ts_language(language: str) -> Language | None:
    """The tree-sitter Language for a grammar-backed language, or None if
    `language` has no grammar registered (e.g. "markdown", "json")."""
    if language not in _CONFIGS:
        return None
    return _get_ts_language(language)
