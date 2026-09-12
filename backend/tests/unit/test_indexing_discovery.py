from pathlib import Path

from app.indexing.discovery import discover_files


def _write(root: Path, relative: str, content: str = "") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_discovers_source_files(tmp_path: Path) -> None:
    _write(tmp_path, "src/main.py", "print('hi')\n")
    _write(tmp_path, "README.md", "# Title\n")

    files = discover_files(tmp_path, max_file_size_bytes=1_000_000, max_files=100)

    assert {f.path for f in files} == {"src/main.py", "README.md"}


def test_denylisted_directories_are_skipped(tmp_path: Path) -> None:
    _write(tmp_path, "src/main.py", "print('hi')\n")
    _write(tmp_path, "node_modules/pkg/index.js", "module.exports = {};\n")
    _write(tmp_path, ".git/HEAD", "ref: refs/heads/main\n")
    _write(tmp_path, "__pycache__/main.cpython-312.pyc", "junk")

    files = discover_files(tmp_path, max_file_size_bytes=1_000_000, max_files=100)

    assert {f.path for f in files} == {"src/main.py"}


def test_gitignore_patterns_are_respected(tmp_path: Path) -> None:
    _write(tmp_path, ".gitignore", "*.log\nbuild/\n")
    _write(tmp_path, "app.py", "x = 1\n")
    _write(tmp_path, "debug.log", "trace\n")
    _write(tmp_path, "build/output.txt", "compiled\n")

    files = discover_files(tmp_path, max_file_size_bytes=1_000_000, max_files=100)

    assert {f.path for f in files} == {".gitignore", "app.py"}


def test_binary_files_are_excluded(tmp_path: Path) -> None:
    _write(tmp_path, "app.py", "x = 1\n")
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00binary\x00data")

    files = discover_files(tmp_path, max_file_size_bytes=1_000_000, max_files=100)

    assert {f.path for f in files} == {"app.py"}


def test_oversized_files_are_excluded(tmp_path: Path) -> None:
    _write(tmp_path, "small.py", "x = 1\n")
    _write(tmp_path, "huge.py", "x" * 5000)

    files = discover_files(tmp_path, max_file_size_bytes=100, max_files=100)

    assert {f.path for f in files} == {"small.py"}


def test_empty_files_are_excluded(tmp_path: Path) -> None:
    _write(tmp_path, "empty.py", "")
    _write(tmp_path, "nonempty.py", "x = 1\n")

    files = discover_files(tmp_path, max_file_size_bytes=1_000_000, max_files=100)

    assert {f.path for f in files} == {"nonempty.py"}


def test_max_files_caps_discovery(tmp_path: Path) -> None:
    for i in range(10):
        _write(tmp_path, f"file_{i}.py", "x = 1\n")

    files = discover_files(tmp_path, max_file_size_bytes=1_000_000, max_files=3)

    assert len(files) == 3


def test_language_is_detected_from_extension(tmp_path: Path) -> None:
    _write(tmp_path, "app.py", "x = 1\n")
    _write(tmp_path, "app.ts", "const x = 1;\n")
    _write(tmp_path, "app.go", "package main\n")
    _write(tmp_path, "notes.txt", "plain text\n")

    files = {
        f.path: f.language
        for f in discover_files(tmp_path, max_file_size_bytes=1_000_000, max_files=100)
    }

    assert files["app.py"] == "python"
    assert files["app.ts"] == "typescript"
    assert files["app.go"] == "go"
    assert files["notes.txt"] is None
