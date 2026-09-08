from app.indexing.chunker import extract
from app.indexing.parser import parse_source

PYTHON_SOURCE = b'''import os
from typing import List

class Greeter:
    """Greets people."""

    def greet(self, name):
        """Say hello."""
        return f"hello {name}"

def standalone(x):
    return x * 2
'''

JS_SOURCE = b"""import { foo } from \"./foo\";

/**
 * Adds two numbers.
 */
function add(a, b) {
  return a + b;
}

class Widget {
  render() {
    return null;
  }
}
"""


def test_python_symbols_and_chunks_follow_ast_boundaries() -> None:
    parsed = parse_source(PYTHON_SOURCE, "python")
    result = extract(parsed, PYTHON_SOURCE.decode(), "python", max_chunk_lines=200)

    symbol_names = {(s.symbol_type, s.name) for s in result.symbols}
    assert symbol_names == {
        ("class", "Greeter"),
        ("method", "greet"),
        ("function", "standalone"),
    }
    assert [(i.text, i.line) for i in result.imports] == [
        ("import os", 1),
        ("from typing import List", 2),
    ]

    greeter = next(s for s in result.symbols if s.name == "Greeter")
    assert greeter.docstring == "Greets people."
    greet = next(s for s in result.symbols if s.name == "greet")
    assert greet.docstring == "Say hello."
    assert greet.parent_index == result.symbols.index(greeter)

    # The class chunk covers only the header (docstring), not the method
    # body — the method already has its own chunk. No chunk duplicates
    # another chunk's content.
    class_chunk = next(c for c in result.chunks if c.chunk_type == "class")
    assert "def greet" not in class_chunk.content
    method_chunk = next(c for c in result.chunks if c.chunk_type == "method")
    assert "hello" in method_chunk.content


def test_javascript_leading_jsdoc_comment_is_captured_as_docstring() -> None:
    parsed = parse_source(JS_SOURCE, "javascript")
    result = extract(parsed, JS_SOURCE.decode(), "javascript", max_chunk_lines=200)

    add_symbol = next(s for s in result.symbols if s.name == "add")
    assert add_symbol.docstring == "Adds two numbers."

    render_symbol = next(s for s in result.symbols if s.name == "render")
    assert render_symbol.symbol_type == "method"


def test_chunk_content_hash_is_stable_for_identical_content() -> None:
    parsed = parse_source(PYTHON_SOURCE, "python")
    first = extract(parsed, PYTHON_SOURCE.decode(), "python", max_chunk_lines=200)
    second = extract(parsed, PYTHON_SOURCE.decode(), "python", max_chunk_lines=200)

    first_hashes = {c.content_hash for c in first.chunks}
    second_hashes = {c.content_hash for c in second.chunks}
    assert first_hashes == second_hashes


def test_never_splits_a_single_symbol_by_raw_character_offset() -> None:
    """A function chunk is exactly the function's AST span — no chunk ever
    starts or ends mid-statement the way a fixed character-count split
    would produce."""
    parsed = parse_source(PYTHON_SOURCE, "python")
    result = extract(parsed, PYTHON_SOURCE.decode(), "python", max_chunk_lines=200)

    standalone_chunk = next(c for c in result.chunks if c.chunk_type == "function")
    assert standalone_chunk.content.strip().startswith("def standalone(x):")
    assert standalone_chunk.content.strip().endswith("return x * 2")


def test_markdown_falls_back_to_heading_aware_prose_chunking() -> None:
    text = "# Title\n\nIntro paragraph.\n\n## Section A\n\nBody A.\n\n## Section B\n\nBody B.\n"

    result = extract(None, text, "markdown", max_chunk_lines=200)

    assert len(result.symbols) == 0
    assert [c.content.splitlines()[0] for c in result.chunks] == [
        "# Title",
        "## Section A",
        "## Section B",
    ]


def test_unrecognized_language_still_gets_indexed_via_prose_fallback() -> None:
    result = extract(None, "line one\nline two\n", None, max_chunk_lines=200)

    assert len(result.chunks) == 1
    assert "line one" in result.chunks[0].content


def test_prose_chunking_never_splits_inside_a_line() -> None:
    lines = [f"paragraph line {i}" for i in range(10)]
    text = "\n".join(lines)

    result = extract(None, text, "markdown", max_chunk_lines=3)

    reconstructed_lines = []
    for chunk in result.chunks:
        reconstructed_lines.extend(chunk.content.splitlines())
    assert reconstructed_lines == lines
