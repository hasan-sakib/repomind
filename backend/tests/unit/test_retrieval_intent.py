from app.domain.chat_status import QueryIntent
from app.retrieval.intent import detect_intent, extract_symbol_name


def test_explain_intent() -> None:
    assert detect_intent("Explain the authentication flow.") == QueryIntent.EXPLAIN


def test_locate_intent() -> None:
    assert detect_intent("Where is payment processing implemented?") == QueryIntent.LOCATE


def test_dependency_intent() -> None:
    assert detect_intent("Which services depend on UserService?") == QueryIntent.DEPENDENCY


def test_explain_how_does_intent() -> None:
    assert detect_intent("How does refresh token rotation work?") == QueryIntent.EXPLAIN


def test_locate_show_me_intent() -> None:
    assert detect_intent("Show me the files involved in checkout.") == QueryIntent.LOCATE


def test_history_intent() -> None:
    assert detect_intent("When was the rate limiter changed?") == QueryIntent.HISTORY
    assert detect_intent("Why did we change the retry logic?") == QueryIntent.HISTORY


def test_general_fallback_intent() -> None:
    assert detect_intent("checkout") == QueryIntent.GENERAL


def test_extract_symbol_name_finds_pascal_case_identifier() -> None:
    assert extract_symbol_name("Which services depend on UserService?") == "UserService"
    assert extract_symbol_name("What does PaymentProcessor depend on?") == "PaymentProcessor"


def test_extract_symbol_name_returns_none_when_nothing_looks_like_a_symbol() -> None:
    assert extract_symbol_name("how does refresh token rotation work") is None


def test_extract_symbol_name_ignores_leading_question_words() -> None:
    assert extract_symbol_name("Where is UserService implemented?") == "UserService"
