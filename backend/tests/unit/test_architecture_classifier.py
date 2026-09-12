from app.architecture.classifier import classify_path


def test_classifies_route_files() -> None:
    assert classify_path("app/api/v1/routes/auth.py") == "route"
    assert classify_path("src/controllers/user_controller.ts") == "route"


def test_classifies_service_files() -> None:
    assert classify_path("app/services/auth_service.py") == "service"


def test_classifies_repository_files() -> None:
    assert classify_path("app/repositories/user_repository.py") == "repository"
    assert classify_path("app/dao/user_dao.py") == "repository"


def test_classifies_model_files() -> None:
    assert classify_path("app/models/user.py") == "model"
    assert classify_path("app/models/product.py") == "model"


def test_classifies_schema_files() -> None:
    assert classify_path("app/schemas/chat.py") == "schema"


def test_unrecognized_path_is_other() -> None:
    assert classify_path("app/main.py") == "other"
    assert classify_path("scripts/seed.py") == "other"


def test_classification_is_case_insensitive() -> None:
    assert classify_path("APP/SERVICES/AuthService.py") == "service"


def test_matches_whole_path_segments_only() -> None:
    """A directory literally named e.g. "modeling" must not match "model"
    — classify_path checks whole path segments, not substrings."""
    assert classify_path("app/modeling/experiment.py") == "other"
