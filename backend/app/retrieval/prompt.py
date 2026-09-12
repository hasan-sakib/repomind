"""Builds the system prompt and numbered context block fed to the LLM.
Source references shown to the user (app/schemas/chat.py's `sources`
field) always come from the RetrievalResult rows persisted by
app/services/chat_service.py — not from parsing the model's citation
markers — so a citation's file/line is a database fact, never a
hallucinated number. The `[N]` markers this prompt asks the model to use
are only there to let the frontend highlight *which* retrieved source
the model actually leaned on; every retrieved chunk is a valid source
whether or not the model happens to cite it.
"""

from app.retrieval.types import RetrievedChunk

SYSTEM_PROMPT = """You are RepoMind, a code intelligence assistant. You answer questions about \
ONE specific connected repository using only the CONTEXT provided below — never general \
knowledge about how other codebases or frameworks typically work, unless the context is \
genuinely insufficient, in which case say so explicitly rather than guessing.

Rules:
- Ground every claim in the numbered context sources. Refer to a source inline as [N] where N \
is its number, right after the sentence it supports.
- If the context doesn't contain enough information to answer, say what's missing instead of \
speculating.
- Prefer concrete references (function/class names, file paths) over vague descriptions.
- Write for a developer who can already read code — be precise and skip generic explanations \
of well-known language features.
- Format your answer in Markdown. Use fenced code blocks with a language tag when quoting code."""


def build_context_block(chunks: list[RetrievedChunk], *, max_chars: int) -> str:
    parts: list[str] = []
    used_chars = 0
    for i, chunk in enumerate(chunks, start=1):
        header = _source_header(i, chunk)
        block = f"{header}\n```\n{chunk.content}\n```"
        if used_chars + len(block) > max_chars and parts:
            break
        parts.append(block)
        used_chars += len(block)
    return "\n\n".join(parts)


def _source_header(index: int, chunk: RetrievedChunk) -> str:
    if chunk.file_path is None:
        return f"[{index}] Commit {(chunk.commit_sha or '')[:7]}"
    if chunk.start_line is not None and chunk.end_line is not None:
        if chunk.start_line == chunk.end_line:
            location = f"line {chunk.start_line}"
        else:
            location = f"lines {chunk.start_line}-{chunk.end_line}"
        return f"[{index}] {chunk.file_path} ({location})"
    return f"[{index}] {chunk.file_path}"


def build_user_message(query: str, context_block: str) -> str:
    if not context_block:
        return f"CONTEXT:\n(no relevant context was found in this repository)\n\nQUESTION:\n{query}"
    return f"CONTEXT:\n{context_block}\n\nQUESTION:\n{query}"
