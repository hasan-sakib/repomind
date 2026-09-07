from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"

    # Web app origin(s) allowed to call this API.
    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: str = Field(
        default="postgresql+asyncpg://repomind:repomind@localhost:5432/repomind"
    )

    # GitHub OAuth App / GitHub App credentials.
    github_client_id: str = ""
    github_client_secret: str = ""
    github_webhook_secret: str = ""

    # Session / auth signing.
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"

    # AI provider configuration. Provider is swappable — see app/ai/provider.py.
    ai_provider: Literal["anthropic"] = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"


@lru_cache
def get_settings() -> Settings:
    return Settings()
