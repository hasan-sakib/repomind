"""Parses and validates the LLM's JSON response for one PR analysis.

Parsing alone isn't enough to satisfy "the analysis must cite actual
repository files" — a syntactically valid JSON object can still name a
file that was never shown to the model. `validate_citations` is the
actual enforcement: it drops any citation pointing outside the set of
paths the prompt (app/pr_analysis/prompt.py) actually gave the model,
rather than trusting the model followed that instruction.
"""

import json
import logging
from typing import Literal

from pydantic import BaseModel, ValidationError

logger = logging.getLogger("repomind.pr_analysis")


class AffectedComponentModel(BaseModel):
    name: str
    file_paths: list[str] = []


class PotentialConcernModel(BaseModel):
    description: str
    file_path: str | None = None
    symbol_name: str | None = None


class RecommendedTestModel(BaseModel):
    description: str
    existing_test_file: str | None = None


class PRAnalysisResult(BaseModel):
    summary: str
    risk_level: Literal["low", "medium", "high"]
    affected_components: list[AffectedComponentModel] = []
    potential_concerns: list[PotentialConcernModel] = []
    recommended_tests: list[RecommendedTestModel] = []


class PRAnalysisParseError(Exception):
    pass


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```")
        stripped = stripped.removesuffix("```")
    return stripped.strip()


def parse_llm_output(text: str) -> PRAnalysisResult:
    try:
        payload = json.loads(_strip_code_fence(text))
    except json.JSONDecodeError as exc:
        raise PRAnalysisParseError(f"Response was not valid JSON: {exc}") from exc
    try:
        return PRAnalysisResult.model_validate(payload)
    except ValidationError as exc:
        raise PRAnalysisParseError(f"Response JSON didn't match the expected shape: {exc}") from exc


def validate_citations(result: PRAnalysisResult, valid_paths: set[str]) -> PRAnalysisResult:
    """Drops any file-path citation the model produced that wasn't one of
    the paths it was actually shown. An affected-component entry that
    loses every one of its file paths this way is dropped entirely — an
    "affected component" with no real files backing it isn't a citation,
    it's a guess."""
    dropped = 0

    components: list[AffectedComponentModel] = []
    for component in result.affected_components:
        kept_paths = [p for p in component.file_paths if p in valid_paths]
        dropped += len(component.file_paths) - len(kept_paths)
        if kept_paths:
            components.append(AffectedComponentModel(name=component.name, file_paths=kept_paths))

    concerns: list[PotentialConcernModel] = []
    for concern in result.potential_concerns:
        file_path = concern.file_path
        if file_path is not None and file_path not in valid_paths:
            dropped += 1
            file_path = None
        concerns.append(
            PotentialConcernModel(
                description=concern.description,
                file_path=file_path,
                symbol_name=concern.symbol_name,
            )
        )

    tests: list[RecommendedTestModel] = []
    for test in result.recommended_tests:
        existing_test_file = test.existing_test_file
        if existing_test_file is not None and existing_test_file not in valid_paths:
            dropped += 1
            existing_test_file = None
        tests.append(
            RecommendedTestModel(
                description=test.description, existing_test_file=existing_test_file
            )
        )

    if dropped:
        logger.warning(
            "PR analysis: dropped %d citation(s) pointing outside the shown files", dropped
        )

    return PRAnalysisResult(
        summary=result.summary,
        risk_level=result.risk_level,
        affected_components=components,
        potential_concerns=concerns,
        recommended_tests=tests,
    )
