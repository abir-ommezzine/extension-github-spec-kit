# app/core/llm_client.py
"""
LLM Client — Provider-agnostic LLM client manager with rate limiting & retry logic

Supports multiple providers:
- Ollama (local)
- OpenAI
- Anthropic
- Groq (OpenAI-compatible)
- NVIDIA NIM (OpenAI-compatible)
- Hugging Face Inference API (OpenAI-compatible)
- Any OpenAI-compatible API (vLLM, LM Studio, etc.)

Provider is selected via LLM_PROVIDER in .env. Provides a unified interface
(chat_completion / chat_completion_structured / get_default_model) for all
agent services, so switching providers never requires touching service code.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
import time
import logging
from openai import OpenAI, RateLimitError, APITimeoutError
from anthropic import Anthropic, RateLimitError as AnthropicRateLimitError
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

# Rate limit / timeout retry configuration
MAX_RETRIES = 3
BASE_DELAY = 5  # seconds
MAX_DELAY = 60  # seconds


def retry_on_rate_limit(func):
    """Decorator to retry on rate limit errors and slow/cold-start timeouts,
    with exponential backoff."""
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except (RateLimitError, AnthropicRateLimitError, APITimeoutError) as e:
                last_exception = e
                if attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                    logger.warning(f"Rate limit/timeout hit (attempt {attempt + 1}/{MAX_RETRIES}), waiting {delay}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"Max retries ({MAX_RETRIES}) exceeded for rate limit/timeout")
                    raise
            except Exception as e:
                error_str = str(e).lower()
                if "rate limit" in error_str or "429" in error_str or "timeout" in error_str or "timed out" in error_str:
                    last_exception = e
                    if attempt < MAX_RETRIES - 1:
                        delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                        logger.warning(f"Rate limit/timeout detected (attempt {attempt + 1}/{MAX_RETRIES}), waiting {delay}s: {e}")
                        time.sleep(delay)
                    else:
                        logger.error(f"Max retries ({MAX_RETRIES}) exceeded for rate limit/timeout")
                        raise
                else:
                    raise
        raise last_exception
    return wrapper


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def chat_completion(self, messages: list[dict], model: str, **kwargs) -> Any:
        pass

    @abstractmethod
    def chat_completion_structured(self, messages: list[dict], model: str, response_format: type[BaseModel], **kwargs) -> Any:
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        pass


class OllamaProvider(LLMProvider):
    """Ollama provider, via its OpenAI-compatible endpoint (/v1) — keeps the
    response shape (.choices[0].message.content) identical across every
    provider, which every agent service relies on."""

    def __init__(self):
        self.client = OpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key=settings.OLLAMA_API_KEY or "ollama"
        )

    @retry_on_rate_limit
    def chat_completion(self, messages: list[dict], model: str, **kwargs) -> Any:
        return self.client.chat.completions.create(model=model, messages=messages, **kwargs)

    @retry_on_rate_limit
    def chat_completion_structured(self, messages: list[dict], model: str, response_format: type[BaseModel], **kwargs) -> Any:
        return self.client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=response_format,
            **kwargs
        )

    def get_default_model(self) -> str:
        return settings.OLLAMA_MODEL


class OpenAIProvider(LLMProvider):
    """OpenAI provider"""

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )

    @retry_on_rate_limit
    def chat_completion(self, messages: list[dict], model: str, **kwargs) -> Any:
        return self.client.chat.completions.create(model=model, messages=messages, **kwargs)

    @retry_on_rate_limit
    def chat_completion_structured(self, messages: list[dict], model: str, response_format: type[BaseModel], **kwargs) -> Any:
        return self.client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=response_format,
            **kwargs
        )

    def get_default_model(self) -> str:
        return settings.OPENAI_MODEL


class AnthropicProvider(LLMProvider):
    """Anthropic (Claude) provider"""

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    @retry_on_rate_limit
    def chat_completion(self, messages: list[dict], model: str, **kwargs) -> Any:
        system_msg = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)

        return self.client.messages.create(
            model=model,
            system=system_msg,
            messages=user_messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            **{k: v for k, v in kwargs.items() if k != "max_tokens"}
        )

    @retry_on_rate_limit
    def chat_completion_structured(self, messages: list[dict], model: str, response_format: type[BaseModel], **kwargs) -> Any:
        # Anthropic has no native structured output — use JSON mode via prompt engineering.
        import json
        schema = response_format.model_json_schema()

        system_prompt = f"""You are a helpful assistant. Respond ONLY with valid JSON matching this schema:
{json.dumps(schema, indent=2)}"""

        response = self.client.messages.create(
            model=model,
            system=system_prompt,
            messages=[m for m in messages if m["role"] != "system"],
            max_tokens=kwargs.get("max_tokens", 4096),
        )

        content = response.content[0].text if response.content else "{}"
        try:
            parsed = json.loads(content)
            return response_format(**parsed)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return response_format(**parsed)
            raise ValueError(f"Failed to parse structured output: {content}")

    def get_default_model(self) -> str:
        return settings.ANTHROPIC_MODEL


class OpenAICompatibleProvider(LLMProvider):
    """Generic OpenAI-compatible provider (Groq, NVIDIA NIM, Hugging Face, vLLM, LM Studio, etc.)"""

    def __init__(self, base_url: str, api_key: str, default_model: str, supports_structured_output: bool = False, timeout: float = 60.0):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )
        self._default_model = default_model
        self._supports_structured = supports_structured_output

    @retry_on_rate_limit
    def chat_completion(self, messages: list[dict], model: str, **kwargs) -> Any:
        return self.client.chat.completions.create(model=model, messages=messages, **kwargs)

    @retry_on_rate_limit
    def chat_completion_structured(self, messages: list[dict], model: str, response_format: type[BaseModel], **kwargs) -> Any:
        if self._supports_structured:
            return self.client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=response_format,
                **kwargs
            )

        # Fallback: JSON mode with prompt engineering (like Anthropic).
        import json
        schema = response_format.model_json_schema()

        system_prompt = f"""You are a helpful assistant. Respond ONLY with valid JSON matching this schema:
{json.dumps(schema, indent=2)}"""

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                *[m for m in messages if m["role"] != "system"]
            ],
            response_format={"type": "json_object"},
            **kwargs
        )

        content = response.choices[0].message.content
        try:
            parsed = json.loads(content)
            return response_format(**parsed)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return response_format(**parsed)
            raise ValueError(f"Failed to parse structured output: {content}")

    def get_default_model(self) -> str:
        return self._default_model


# Provider factory
def get_provider() -> LLMProvider:
    """Factory function to get the configured provider"""
    provider_type = settings.LLM_PROVIDER

    if provider_type == "ollama":
        return OllamaProvider()
    elif provider_type == "openai":
        return OpenAIProvider()
    elif provider_type == "anthropic":
        return AnthropicProvider()
    elif provider_type == "groq":
        return OpenAICompatibleProvider(
            base_url=settings.GROQ_BASE_URL,
            api_key=settings.GROQ_API_KEY,
            default_model=settings.GROQ_MODEL,
            supports_structured_output=False,  # Groq doesn't support json_schema response_format
            timeout=60.0
        )
    elif provider_type == "nvidia":
        return OpenAICompatibleProvider(
            base_url=settings.NVIDIA_BASE_URL,
            api_key=settings.NVIDIA_API_KEY,
            default_model=settings.NVIDIA_MODEL,
            supports_structured_output=False,  # NVIDIA NIM doesn't support json_schema
            timeout=420.0  # Longer timeout for NVIDIA NIM cold starts + larger agent payloads (summary/glossary/diagram)
        )
    elif provider_type == "huggingface":
        return OpenAICompatibleProvider(
            base_url=settings.HUGGINGFACE_BASE_URL,
            api_key=settings.HUGGINGFACE_API_KEY,
            default_model=settings.HUGGINGFACE_MODEL,
            supports_structured_output=False,  # HF Inference API doesn't support json_schema
            timeout=120.0
        )
    elif provider_type == "openai_compatible":
        return OpenAICompatibleProvider(
            base_url=settings.OPENAI_COMPATIBLE_BASE_URL or "http://localhost:11434/v1",
            api_key=settings.OPENAI_COMPATIBLE_API_KEY or "ollama",
            default_model=settings.OPENAI_COMPATIBLE_MODEL,
            supports_structured_output=True  # Assume compatible APIs support it
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}")


# Global provider instance (lazy singleton — built on first use, so importing
# this module never requires every provider's API key to be set).
_provider: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """Get the global LLM provider instance (singleton)"""
    global _provider
    if _provider is None:
        _provider = get_provider()
    return _provider


def get_default_model() -> str:
    """Get the default model for the currently configured provider (LLM_PROVIDER)"""
    return get_llm_provider().get_default_model()


def chat_completion(messages: list[dict], model: Optional[str] = None, **kwargs) -> Any:
    """Unified chat completion interface — routes to whichever provider LLM_PROVIDER selects."""
    provider = get_llm_provider()
    model = model or provider.get_default_model()
    return provider.chat_completion(messages, model, **kwargs)


def chat_completion_structured(messages: list[dict], response_format: type[BaseModel], model: Optional[str] = None, **kwargs) -> Any:
    """Unified structured chat completion interface (returns a validated Pydantic model)."""
    provider = get_llm_provider()
    model = model or provider.get_default_model()
    return provider.chat_completion_structured(messages, model, response_format, **kwargs)