"""Parses and validates the LLM's JSON response for the onboarding
guide's AI-written sections. Mirrors app/pr_analysis/result_schema.py
(ADR 0007): parsing alone doesn't satisfy "don't cite files the model
wasn't shown" — `validate_citations` drops any FAQ citation pointing
outside the set of paths the prompt actually gave the model."""

import json
import logging

from pydantic import BaseModel, ValidationError

logger = logging.getLogger("repomind.onboarding")


class FaqEntryModel(BaseModel):
    question: str
    answer: str
    file_paths: list[str] = []


class OnboardingGuideResult(BaseModel):
    architecture_overview: str
    common_workflows: str
    authentication_flow: str | None = None
    faq: list[FaqEntryModel] = []


class OnboardingParseError(Exception):
    pass


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```")
        stripped = stripped.removesuffix("```")
    return stripped.strip()


def parse_llm_output(text: str) -> OnboardingGuideResult:
    try:
        payload = json.loads(_strip_code_fence(text))
    except json.JSONDecodeError as exc:
        raise OnboardingParseError(f"Response was not valid JSON: {exc}") from exc
    try:
        return OnboardingGuideResult.model_validate(payload)
    except ValidationError as exc:
        raise OnboardingParseError(f"Response JSON didn't match the expected shape: {exc}") from exc


def validate_citations(
    result: OnboardingGuideResult, valid_paths: set[str]
) -> OnboardingGuideResult:
    dropped = 0
    faq: list[FaqEntryModel] = []
    for entry in result.faq:
        kept_paths = [p for p in entry.file_paths if p in valid_paths]
        dropped += len(entry.file_paths) - len(kept_paths)
        faq.append(
            FaqEntryModel(question=entry.question, answer=entry.answer, file_paths=kept_paths)
        )

    if dropped:
        logger.warning(
            "Onboarding guide: dropped %d FAQ citation(s) pointing outside the shown files", dropped
        )

    return OnboardingGuideResult(
        architecture_overview=result.architecture_overview,
        common_workflows=result.common_workflows,
        authentication_flow=result.authentication_flow,
        faq=faq,
    )
