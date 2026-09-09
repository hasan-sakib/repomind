import pytest

from app.pr_analysis.result_schema import (
    PRAnalysisParseError,
    PRAnalysisResult,
    parse_llm_output,
    validate_citations,
)

VALID_JSON = """{
  "summary": "Adds refresh-token rotation to the auth service.",
  "risk_level": "high",
  "affected_components": [
    {"name": "Authentication", "file_paths": ["app/services/auth_service.py"]}
  ],
  "potential_concerns": [
    {
      "description": "Refresh token logic changed",
      "file_path": "app/services/auth_service.py",
      "symbol_name": "AuthService"
    }
  ],
  "recommended_tests": [
    {"description": "Refresh token flow", "existing_test_file": "tests/test_auth_service.py"}
  ]
}"""


def test_parses_plain_json() -> None:
    result = parse_llm_output(VALID_JSON)
    assert result.risk_level == "high"
    assert result.affected_components[0].name == "Authentication"


def test_strips_markdown_code_fence() -> None:
    fenced = f"```json\n{VALID_JSON}\n```"
    result = parse_llm_output(fenced)
    assert result.summary.startswith("Adds refresh-token rotation")


def test_invalid_json_raises_parse_error() -> None:
    with pytest.raises(PRAnalysisParseError):
        parse_llm_output("not json at all")


def test_valid_json_missing_required_field_raises_parse_error() -> None:
    with pytest.raises(PRAnalysisParseError):
        parse_llm_output('{"summary": "missing risk_level"}')


def test_validate_citations_keeps_paths_the_model_was_shown() -> None:
    result = parse_llm_output(VALID_JSON)
    valid_paths = {"app/services/auth_service.py", "tests/test_auth_service.py"}

    validated = validate_citations(result, valid_paths)

    assert validated.affected_components[0].file_paths == ["app/services/auth_service.py"]
    assert validated.potential_concerns[0].file_path == "app/services/auth_service.py"
    assert validated.recommended_tests[0].existing_test_file == "tests/test_auth_service.py"


def test_validate_citations_drops_hallucinated_paths() -> None:
    result = parse_llm_output(VALID_JSON)
    # The model was never shown this path — must not survive validation.
    valid_paths: set[str] = set()

    validated = validate_citations(result, valid_paths)

    assert validated.affected_components == []  # lost its only file path -> dropped entirely
    assert validated.potential_concerns[0].file_path is None  # citation nulled, concern kept
    assert validated.potential_concerns[0].description == "Refresh token logic changed"
    assert validated.recommended_tests[0].existing_test_file is None


def test_validate_citations_is_pure_does_not_mutate_input() -> None:
    result = parse_llm_output(VALID_JSON)
    validate_citations(result, set())
    # The original parsed result is untouched by validation.
    assert result.affected_components[0].file_paths == ["app/services/auth_service.py"]


def test_result_model_defaults_to_empty_lists() -> None:
    result = PRAnalysisResult(summary="Trivial change.", risk_level="low")
    assert result.affected_components == []
    assert result.potential_concerns == []
    assert result.recommended_tests == []
