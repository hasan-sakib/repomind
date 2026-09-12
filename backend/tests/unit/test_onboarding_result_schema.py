import pytest

from app.onboarding.result_schema import (
    OnboardingGuideResult,
    OnboardingParseError,
    parse_llm_output,
    validate_citations,
)

VALID_JSON = """{
  "architecture_overview": "Requests enter through app/api/routes/auth.py, which calls \
AuthService in app/services/auth_service.py, which persists through UserRepository.",
  "common_workflows": "A login request is handled by AuthController, which calls \
AuthService.login.",
  "authentication_flow": "AuthService issues and validates tokens for every request.",
  "faq": [
    {
      "question": "How is authentication handled?",
      "answer": "See AuthService.",
      "file_paths": ["app/services/auth_service.py"]
    }
  ]
}"""


def test_parses_plain_json() -> None:
    result = parse_llm_output(VALID_JSON)
    assert result.authentication_flow is not None
    assert result.faq[0].question == "How is authentication handled?"


def test_strips_markdown_code_fence() -> None:
    fenced = f"```json\n{VALID_JSON}\n```"
    result = parse_llm_output(fenced)
    assert result.architecture_overview.startswith("Requests enter")


def test_authentication_flow_can_be_null() -> None:
    payload = (
        '{"architecture_overview": "x", "common_workflows": "y", '
        '"authentication_flow": null, "faq": []}'
    )
    result = parse_llm_output(payload)
    assert result.authentication_flow is None


def test_invalid_json_raises_parse_error() -> None:
    with pytest.raises(OnboardingParseError):
        parse_llm_output("not json at all")


def test_missing_required_field_raises_parse_error() -> None:
    with pytest.raises(OnboardingParseError):
        parse_llm_output('{"architecture_overview": "only this"}')


def test_validate_citations_keeps_shown_paths() -> None:
    result = parse_llm_output(VALID_JSON)
    validated = validate_citations(result, {"app/services/auth_service.py"})
    assert validated.faq[0].file_paths == ["app/services/auth_service.py"]


def test_validate_citations_drops_hallucinated_paths() -> None:
    result = parse_llm_output(VALID_JSON)
    validated = validate_citations(result, set())
    assert validated.faq[0].file_paths == []
    # The question/answer text itself survives — only the citation is dropped.
    assert validated.faq[0].question == "How is authentication handled?"


def test_validate_citations_does_not_mutate_input() -> None:
    result = parse_llm_output(VALID_JSON)
    validate_citations(result, set())
    assert result.faq[0].file_paths == ["app/services/auth_service.py"]


def test_result_model_defaults() -> None:
    result = OnboardingGuideResult(architecture_overview="x", common_workflows="y")
    assert result.authentication_flow is None
    assert result.faq == []
