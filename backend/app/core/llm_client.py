# app/core/llm_client.py
"""
LLM Client — Provider-agnostic LLM client manager

Supports multiple providers:
- Ollama (local)
- OpenAI
- Anthropic
- Groq (OpenAI-compatible)
- Any OpenAI-compatible API (vLLM, LM Studio, etc.)

Provides a unified interface for all services.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from openai import OpenAI
from anthropic import Anthropic
import ollama
from pydantic import BaseModel

from app.config import settings


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
    """Ollama provider (native client)"""
    
    def __init__(self):
        self.client = ollama.Client(
            host=settings.OLLAMA_BASE_URL,
            headers={"Authorization": f"Bearer {settings.OLLAMA_API_KEY}"} if settings.OLLAMA_API_KEY else None
        )
        self.openai_client = OpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key=settings.OLLAMA_API_KEY or "ollama"
        )
    
    def chat_completion(self, messages: list[dict], model: str, **kwargs) -> Any:
        return self.client.chat(model=model, messages=messages, **kwargs)
    
    def chat_completion_structured(self, messages: list[dict], model: str, response_format: type[BaseModel], **kwargs) -> Any:
        return self.openai_client.beta.chat.completions.parse(
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
    
    def chat_completion(self, messages: list[dict], model: str, **kwargs) -> Any:
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
    
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
    
    def chat_completion(self, messages: list[dict], model: str, **kwargs) -> Any:
        # Convert OpenAI format to Anthropic format
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
    
    def chat_completion_structured(self, messages: list[dict], model: str, response_format: type[BaseModel], **kwargs) -> Any:
        # Anthropic doesn't have native structured output, use JSON mode with prompt engineering
        import json
        schema = response_format.model_json_schema()
        
        system_prompt = f"""You are a helpful assistant. Respond ONLY with valid JSON matching this schema:
{json.dumps(schema, indent=2)}"""
        
        messages_with_schema = [{"role": "system", "content": system_prompt}] + messages
        
        response = self.client.messages.create(
            model=model,
            system=system_prompt,
            messages=[m for m in messages if m["role"] != "system"],
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        
        # Parse JSON from response
        content = response.content[0].text if response.content else "{}"
        try:
            parsed = json.loads(content)
            return response_format(**parsed)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from text
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return response_format(**parsed)
            raise ValueError(f"Failed to parse structured output: {content}")
    
    def get_default_model(self) -> str:
        return settings.ANTHROPIC_MODEL


class OpenAICompatibleProvider(LLMProvider):
    """Generic OpenAI-compatible provider (Groq, vLLM, LM Studio, etc.)"""
    
    def __init__(self, base_url: str, api_key: str, default_model: str, supports_structured_output: bool = False):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self._default_model = default_model
        self._supports_structured = supports_structured_output
    
    def chat_completion(self, messages: list[dict], model: str, **kwargs) -> Any:
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
    
    def chat_completion_structured(self, messages: list[dict], model: str, response_format: type[BaseModel], **kwargs) -> Any:
        if self._supports_structured:
            return self.client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=response_format,
                **kwargs
            )
        else:
            # Fallback: JSON mode with prompt engineering (like Anthropic)
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
            supports_structured_output=False  # Groq doesn't support json_schema response_format
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


# Global provider instance
_provider: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """Get the global LLM provider instance (singleton)"""
    global _provider
    if _provider is None:
        _provider = get_provider()
    return _provider


# Backward compatibility functions
def get_default_model() -> str:
    """Get the default model for the current provider"""
    return get_llm_provider().get_default_model()


def chat_completion(messages: list[dict], model: Optional[str] = None, **kwargs) -> Any:
    """Unified chat completion interface"""
    provider = get_llm_provider()
    model = model or provider.get_default_model()
    return provider.chat_completion(messages, model, **kwargs)


def chat_completion_structured(messages: list[dict], response_format: type[BaseModel], model: Optional[str] = None, **kwargs) -> Any:
    """Unified structured chat completion interface (returns Pydantic model)"""
    provider = get_llm_provider()
    model = model or provider.get_default_model()
    return provider.chat_completion_structured(messages, model, response_format, **kwargs)


# Legacy exports for backward compatibility
ollama_native_client = None  # Deprecated
ollama_openai_client = None  # Deprecated


def get_ollama_model() -> str:
    """Deprecated: Use get_default_model() instead"""
    import warnings
    warnings.warn("get_ollama_model() is deprecated, use get_default_model()", DeprecationWarning)
    return get_default_model()


# Initialize provider on import (optional - lazy init preferred)
# _provider = get_provider()