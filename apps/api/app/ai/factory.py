from functools import lru_cache

from app.ai.embedding_provider import EmbeddingProvider
from app.ai.provider import AIProvider
from app.ai.providers.anthropic_provider import AnthropicProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.providers.voyage_provider import VoyageEmbeddingProvider
from app.ai.providers.voyage_reranker import VoyageReranker
from app.ai.reranker import Reranker
from app.core.config import get_settings


@lru_cache
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "anthropic":
        return AnthropicProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_model)
    if settings.ai_provider == "ollama":
        return OllamaProvider(host=settings.ollama_host, model=settings.ollama_model)
    raise ValueError(f"Unsupported AI provider: {settings.ai_provider}")


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.embedding_provider == "voyage":
        return VoyageEmbeddingProvider(
            api_key=settings.voyage_api_key,
            model=settings.voyage_model,
            output_dimension=settings.embedding_dimension,
        )
    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")


@lru_cache
def get_reranker() -> Reranker:
    settings = get_settings()
    if settings.reranker_provider == "voyage":
        return VoyageReranker(api_key=settings.voyage_api_key, model=settings.voyage_rerank_model)
    raise ValueError(f"Unsupported reranker provider: {settings.reranker_provider}")
