from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_JWT_SECRET_LENGTH = 32


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
    ai_provider: Literal["anthropic", "ollama"] = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"

    # Ollama — a free, local alternative to Anthropic (app/ai/providers/
    # ollama_provider.py). No API key: `host` just needs a running
    # `ollama serve` reachable at that address, and `model` needs to
    # already be pulled (`ollama pull <model>`) there.
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"

    # Embedding provider — see app/ai/embedding_provider.py. Anthropic has no
    # first-party embeddings API; Voyage is Anthropic's recommended partner
    # and voyage-code-3 is tuned for source code. See
    # docs/architecture/0004-codebase-indexing.md.
    embedding_provider: Literal["voyage"] = "voyage"
    voyage_api_key: str = ""
    voyage_model: str = "voyage-code-3"
    # voyage-code-3 supports Matryoshka output truncation (256/512/1024/2048).
    # 1024 balances retrieval quality against pgvector index size/build time.
    embedding_dimension: int = 1024

    # Background job queue (indexing, re-indexing, embeddings). See
    # docs/architecture/0004-codebase-indexing.md for why arq/Redis replaced
    # Phase 3's FastAPI BackgroundTasks.
    redis_url: str = "redis://localhost:6379"

    # Per-IP rate limits (app/core/rate_limit.py) on the unauthenticated
    # endpoints most attractive to brute-force/abuse — credential stuffing,
    # account enumeration via registration, password-reset email bombing.
    # See docs/architecture/security.md.
    rate_limit_login_per_minute: int = 10
    rate_limit_register_per_minute: int = 5
    rate_limit_refresh_per_minute: int = 30
    rate_limit_password_reset_per_minute: int = 5
    rate_limit_email_verify_per_minute: int = 5

    # Indexing pipeline tunables.
    indexing_max_file_size_bytes: int = 500_000
    indexing_max_files_per_repository: int = 3000
    indexing_max_chunk_lines: int = 200

    # Reranker — see app/ai/reranker.py and docs/architecture/0005-ai-rag-engine.md.
    reranker_provider: Literal["voyage"] = "voyage"
    voyage_rerank_model: str = "rerank-2.5"

    # RAG pipeline tunables (app/retrieval/graph.py).
    rag_vector_candidates: int = 24  # fetched from pgvector before reranking
    rag_context_chunks: int = 8  # kept after reranking, sent to the LLM
    rag_dependency_limit: int = 12
    rag_git_history_limit: int = 5
    rag_max_context_chars: int = 24_000

    # PR analysis tunables (app/pr_analysis/, app/services/pr_analysis_service.py).
    pr_analysis_max_patch_chars_per_file: int = 2_000
    pr_analysis_max_output_tokens: int = 3_000

    # Onboarding guide tunables (app/onboarding/, app/services/onboarding_service.py).
    onboarding_max_output_tokens: int = 4_000

    # Analytics tunables (app/analytics/, app/services/analytics_service.py).
    analytics_stale_issue_days: int = 30
    analytics_top_hotspots: int = 15

    # Billing provider — see app/billing/provider.py. "null" (the only
    # option today) means no real subscription billing is wired up; plan
    # changes happen directly via organization_service.set_plan.
    billing_provider: Literal["null"] = "null"

    @model_validator(mode="after")
    def _require_strong_jwt_secret(self) -> "Settings":
        """A short/empty JWT_SECRET lets anyone forge a session for any
        user (HS256 with a known or empty key is trivially reproducible) —
        this must fail loudly at startup in every environment, not just
        production, rather than silently signing tokens with a weak key.
        See docs/architecture/security.md."""
        if len(self.jwt_secret) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET must be at least {MIN_JWT_SECRET_LENGTH} characters "
                "(generate one with `openssl rand -hex 32`) — refusing to start "
                "with a short or empty secret."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
