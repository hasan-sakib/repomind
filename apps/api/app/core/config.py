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

    # Public URL of the frontend, used to build redirect/email links.
    frontend_url: str = "http://localhost:3000"

    # GitHub OAuth App credentials — login only. See
    # docs/architecture/0002-auth-and-multi-tenancy.md for why this is a
    # separate credential set from the GitHub App below.
    github_client_id: str = ""
    github_client_secret: str = ""

    # GitHub App credentials — repository access (installation tokens) and
    # webhooks only, never user login. See
    # docs/architecture/0003-github-integration.md.
    github_app_id: str = ""
    github_app_slug: str = ""
    github_app_private_key: str = ""
    github_webhook_secret: str = ""

    # Session / auth signing.
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    password_reset_token_ttl_minutes: int = 30
    email_verification_token_ttl_hours: int = 24

    # Whether an unverified email blocks login. Off by default — there is no
    # real email transport configured yet (see app/integrations/email), so
    # enforcing this would lock every user out. Flip once a real provider
    # is wired up.
    require_email_verification: bool = False

    # AI provider configuration. Provider is swappable — see app/ai/provider.py.
    ai_provider: Literal["anthropic"] = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"


@lru_cache
def get_settings() -> Settings:
    return Settings()
