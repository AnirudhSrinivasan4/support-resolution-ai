"""Build the configured LLM adapter once per application process."""

from functools import lru_cache

from app.core.config import settings
from app.domain.ports import LLMProvider
from app.infrastructure.llm.openai_compatible import OpenAICompatibleLLMProvider


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    if settings.llm_provider != "openai-compatible":
        raise RuntimeError("LLM_PROVIDER must be set to openai-compatible")
    try:
        return OpenAICompatibleLLMProvider(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    except ValueError as error:
        raise RuntimeError("LLM provider configuration is invalid") from error
