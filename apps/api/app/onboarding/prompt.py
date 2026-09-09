"""Builds the single prompt used to generate the onboarding guide's four
AI-written sections in one completion call. Every file path the model may
cite is enumerated explicitly (important modules, route/service files,
auth files, database-structure files) — result_schema.py enforces that
server-side rather than trusting the instruction alone, the same pattern
as app/pr_analysis/prompt.py (ADR 0007)."""

from app.onboarding.context import OnboardingContext

SYSTEM_PROMPT = """You are RepoMind's onboarding guide writer. You produce the narrative parts of \
a new developer's onboarding guide for ONE specific repository, grounded entirely in the \
structured facts given to you below — never general knowledge about how other codebases \
typically work.

Rules:
- Every file path or module name you mention MUST be one that was explicitly given to you below. \
Never invent a path.
- "architecture_overview" (2-4 sentences): describe how the real modules listed below relate to \
each other, using their actual names and the dependency edges given — e.g. "X calls into Y, which \
persists through Z." Do not describe a generic layered architecture in the abstract; describe \
THIS repository's actual structure.
- "common_workflows" (2-4 sentences): describe 1-3 concrete request/data flows through the real \
route and service files listed below — e.g. "A request to X is handled by Y, which calls Z."
- "authentication_flow": if AUTHENTICATION-RELATED FILES lists any files, describe how \
authentication actually works using those real files and symbols, in 2-4 sentences. If that \
section says none were found, set "authentication_flow" to null — do not invent an auth flow \
that doesn't exist in this repository.
- "faq": 3-6 question/answer pairs a new developer would actually ask about THIS repository, \
each answer grounded in and citing real file paths from what's given below (file_paths list). \
Do not write generic questions with generic answers ("What is a repository?") — every question \
must be answerable only by looking at this specific repository's actual structure.
- Respond with ONLY a single JSON object matching this exact shape — no prose, no markdown code \
fence, no commentary before or after:

{
  "architecture_overview": str,
  "common_workflows": str,
  "authentication_flow": str | null,
  "faq": [{"question": str, "answer": str, "file_paths": [str, ...]}]
}"""

_RETRY_REMINDER = (
    "Your previous response was not valid JSON matching the required shape. "
    "Respond again with ONLY the JSON object — no other text."
)


def _format_modules(context: OnboardingContext) -> str:
    lines = ["IMPORTANT MODULES:"]
    for module in context.important_modules:
        lines.append(f"- {module.path} ({module.kind}, {module.file_count} files)")
    if context.module_edges:
        lines.append("\nMODULE DEPENDENCIES (source -> target):")
        for edge in context.module_edges:
            lines.append(f"- {edge.source} -> {edge.target}")
    return "\n".join(lines)


def _format_routes_and_services(context: OnboardingContext) -> str:
    lines = []
    if context.route_files:
        lines.append("ROUTE FILES:")
        lines.extend(f"- {r.path} ({r.label})" for r in context.route_files)
    if context.service_files:
        lines.append("\nSERVICE FILES:")
        lines.extend(f"- {r.path} ({r.label})" for r in context.service_files)
    return "\n".join(lines)


def _format_auth(context: OnboardingContext) -> str:
    if not context.auth_files:
        return "AUTHENTICATION-RELATED FILES: none found"
    lines = ["AUTHENTICATION-RELATED FILES:"]
    lines.extend(f"- {f.path}" for f in context.auth_files[:10])
    return "\n".join(lines)


def _format_database(context: OnboardingContext) -> str:
    if not context.database_structure:
        return "DATABASE-STRUCTURE FILES: none found"
    lines = ["DATABASE-STRUCTURE FILES:"]
    lines.extend(
        f"- {e.path}: {e.class_name} ({e.symbol_type})" for e in context.database_structure[:20]
    )
    return "\n".join(lines)


def build_user_message(*, repository_full_name: str, context: OnboardingContext) -> str:
    parts = [f"REPOSITORY: {repository_full_name}", "", _format_modules(context)]
    parts.append(_format_routes_and_services(context))
    parts.append(_format_auth(context))
    parts.append(_format_database(context))
    if context.readme_content:
        parts.append(f"\nREADME (excerpt):\n{context.readme_content}")
    return "\n\n".join(p for p in parts if p)


def build_retry_message(previous_output: str) -> str:
    return f"{_RETRY_REMINDER}\n\nYour previous response was:\n{previous_output[:2000]}"
