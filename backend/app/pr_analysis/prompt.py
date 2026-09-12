"""Builds the prompt handed to the LLM for one PR analysis. Every file
path the model is allowed to reference is enumerated explicitly in this
prompt (changed files, their dependents, related tests) — the model is
instructed to cite only those, and result_schema.py enforces it
server-side rather than trusting the instruction alone."""

from app.pr_analysis.context import ChangedFileContext, PRAnalysisContext

SYSTEM_PROMPT = """You are RepoMind's pull request reviewer. You analyze ONE pull request from \
a specific repository and produce a structured risk assessment for a developer about to review \
it — not a generic code review, a *risk and impact* analysis.

You are given, for each changed file: its status, diff, which of its indexed symbols the diff \
touches, which other files in the repository depend on those symbols, and any existing test \
files that already reference them.

Rules:
- Every file path or symbol name you mention MUST be one that was explicitly given to you below \
— in the changed files, their dependents, or the related test files. Never invent a path.
- Ground "affected_components" in real changed (or dependent) file paths — group by the actual \
subsystem they belong to (e.g. "Authentication", "API Middleware"), not by directory name alone.
- Ground "potential_concerns" in specific, concrete risks — a modified auth check, a changed \
function signature callers still use the old way, a removed validation, a schema change without \
a migration. Cite the file (and symbol, if relevant) each concern is about.
- For "recommended_tests", prefer citing an EXISTING related test file if one was given to you; \
only describe a net-new test scenario when no existing test covers it.
- risk_level is "high" when core auth/security/payment/data-integrity logic changed, many \
dependents are affected, or a change lacks any related test; "medium" for moderate-surface \
changes with some dependents or partial test coverage; "low" for small, well-isolated, \
well-tested changes.
- Respond with ONLY a single JSON object matching this exact shape — no prose, no markdown code \
fence, no commentary before or after:

{
  "summary": "2-4 sentence plain-English summary of what this PR does and why it matters",
  "risk_level": "low" | "medium" | "high",
  "affected_components": [{"name": str, "file_paths": [str, ...]}],
  "potential_concerns": [{"description": str, "file_path": str | null, "symbol_name": str | null}],
  "recommended_tests": [{"description": str, "existing_test_file": str | null}]
}"""

_RETRY_REMINDER = (
    "Your previous response was not valid JSON matching the required shape. "
    "Respond again with ONLY the JSON object — no other text."
)


def _format_file(file: ChangedFileContext) -> str:
    lines = [f"### {file.path} ({file.status}, +{file.additions}/-{file.deletions})"]
    lines.append(f"kind: {file.kind}" + ("" if file.indexed else " — not currently indexed"))
    if file.changed_symbols:
        symbols = ", ".join(
            f"{s.symbol_type} {s.name} (L{s.start_line}-{s.end_line})" for s in file.changed_symbols
        )
        lines.append(f"symbols touched by this diff: {symbols}")
    if file.dependents:
        dependents = ", ".join(f"{d.path} (via {d.matched_name})" for d in file.dependents)
        lines.append(f"depended on by: {dependents}")
    if file.patch_excerpt:
        lines.append(f"diff:\n```diff\n{file.patch_excerpt}\n```")
    return "\n".join(lines)


def build_user_message(*, pr_number: int, pr_title: str, context: PRAnalysisContext) -> str:
    parts = [f"PULL REQUEST #{pr_number}: {pr_title}", "", "CHANGED FILES:"]
    parts.extend(_format_file(f) for f in context.changed_files)

    if context.related_tests:
        parts.append("\nRELATED EXISTING TEST FILES:")
        parts.extend(f"- {t.path} (relates to {t.matched_path})" for t in context.related_tests)
    else:
        parts.append("\nRELATED EXISTING TEST FILES: none found")

    return "\n\n".join(parts)


def build_retry_message(previous_output: str) -> str:
    return f"{_RETRY_REMINDER}\n\nYour previous response was:\n{previous_output[:2000]}"
