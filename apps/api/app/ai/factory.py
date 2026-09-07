from functools import lru_cache

from app.ai.provider import AIProvider
from app.ai.providers.anthropic_provider import AnthropicProvider
from app.core.config import get_settings


@lru_cache
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "anthropic":
        return AnthropicProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_model)
    raise ValueError(f"Unsupported AI provider: {settings.ai_provider}")
