import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_short_jwt_secret_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret="too-short")


def test_empty_jwt_secret_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret="")


def test_strong_jwt_secret_is_accepted() -> None:
    settings = Settings(jwt_secret="a" * 32)
    assert settings.jwt_secret == "a" * 32
