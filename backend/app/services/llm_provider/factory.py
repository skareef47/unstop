"""
LLM Provider Factory
"""
from typing import Optional
from app.core.config import settings
from app.services.llm_provider.base import BaseLLMProvider
from app.services.llm_provider.mock_provider import MockLLMProvider
from app.services.llm_provider.gemini_provider import GeminiProvider
from app.services.llm_provider.openai_provider import OpenAIProvider
from app.services.llm_provider.groq_provider import GroqProvider

_provider_instance: Optional[BaseLLMProvider] = None


def get_llm_provider() -> BaseLLMProvider:
    """Dependency injection provider for LLM adapter."""
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_type = settings.LLM_PROVIDER.lower()

    if provider_type == "gemini":
        try:
            return GeminiProvider()
        except Exception:
            return MockLLMProvider()
    elif provider_type == "openai":
        try:
            return OpenAIProvider()
        except Exception:
            return MockLLMProvider()
    elif provider_type == "groq":
        try:
            return GroqProvider()
        except Exception:
            return MockLLMProvider()
    else:
        return MockLLMProvider()


def set_llm_provider(provider: BaseLLMProvider) -> None:
    """Override provider instance for testing."""
    global _provider_instance
    _provider_instance = provider
