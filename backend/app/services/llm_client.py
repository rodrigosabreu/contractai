"""LLM Client with provider abstraction for NVIDIA and OpenAI."""
import abc
import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel, Field

from app.config import get_settings

settings = get_settings()


@dataclass
class LLMMessage:
    """Message for LLM conversation."""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    input_tokens: int
    output_tokens: int
    total_cost_usd: float
    model: str
    provider: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    async def complete(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> LLMResponse:
        """Complete a chat conversation."""
        ...

    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat conversation."""
        ...

    async def embed(
        self,
        texts: List[str],
        **kwargs,
    ) -> List[List[float]]:
        """Generate embeddings for texts."""
        ...

    @property
    def name(self) -> str:
        """Provider name."""
        ...

    @property
    def model(self) -> str:
        """Model name."""
        ...

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD for token usage."""
        ...


class BaseLLMProvider:
    """Base class for LLM providers with common functionality."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        input_cost_per_1k: float,
        output_cost_per_1k: float,
    ):
        self.api_key = api_key
        self._model = model
        self.base_url = base_url
        self.input_cost_per_1k = input_cost_per_1k
        self.output_cost_per_1k = output_cost_per_1k
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def model(self) -> str:
        return self._model

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens / 1000) * self.input_cost_per_1k + (output_tokens / 1000) * self.output_cost_per_1k

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _parse_usage(self, response: Dict[str, Any]) -> tuple[int, int]:
        """Extract token usage from response. Override in subclasses."""
        usage = response.get("usage", {})
        return usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        super().__init__(
            api_key=api_key,
            model=model,
            base_url="https://api.openai.com/v1",
            input_cost_per_1k=0.01,  # GPT-4 Turbo: $0.01/1k input
            output_cost_per_1k=0.03,  # GPT-4 Turbo: $0.03/1k output
        )

    @property
    def name(self) -> str:
        return "openai"

    async def complete(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> LLMResponse:
        client = await self._get_client()

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        if response_format:
            payload["response_format"] = response_format

        payload.update({k: v for k, v in kwargs.items() if v is not None})

        response = await client.post(f"{self.base_url}/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        input_tokens, output_tokens = self._parse_usage(data)
        cost = self.estimate_cost(input_tokens, output_tokens)
        model = data.get("model")
        direct = (type(self) is OpenAIProvider and
                  str(response.url) == "https://api.openai.com/v1/chat/completions" and
                  isinstance(model, str) and 0 < len(model) <= 200 and model.isascii() and
                  all(c.isalnum() or c in "-_.:/" for c in model))

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost_usd=cost,
            model=self.model,
            provider=self.name,
            metadata={"finish_reason": data["choices"][0].get("finish_reason"),
                      "effective_provider": "openai" if direct else None,
                      "effective_model": model if direct else None},
        )

    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        client = await self._get_client()

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        async with client.stream("POST", f"{self.base_url}/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    async def embed(
        self,
        texts: List[str],
        **kwargs,
    ) -> List[List[float]]:
        client = await self._get_client()

        # Use text-embedding-3-small for cost efficiency (1536 dimensions)
        embed_model = kwargs.get("model", "text-embedding-3-small")

        payload = {
            "model": embed_model,
            "input": texts,
            "encoding_format": "float",
        }

        response = await client.post(f"{self.base_url}/embeddings", json=payload)
        response.raise_for_status()
        data = response.json()

        return [item["embedding"] for item in data["data"]]


class HermesProvider(OpenAIProvider):
    """Hermes API server chat-completions adapter; no embedding endpoint assumed."""

    def __init__(self, api_key: str, model: str, base_url: str):
        super().__init__(api_key=api_key, model=model)
        self.base_url = base_url.rstrip("/")
        self.input_cost_per_1k = 0
        self.output_cost_per_1k = 0

    @property
    def name(self) -> str:
        return "hermes"

    async def complete(self, messages, temperature=0.1, max_tokens=None,
                       response_format=None, **kwargs):
        # AnalysisService passes model=None; don't override the configured model.
        if kwargs.get("model") is None:
            kwargs.pop("model", None)
        result = await super().complete(messages, temperature, max_tokens, response_format, **kwargs)
        # Chat Completions can echo the requested alias, not the upstream model.
        # Do not infer the effective runtime, including after Hermes' own fallback.
        result.model = "unknown"
        result.metadata.update({
            "requested_model": kwargs.get("model", self.model),
            "effective_provider": None,
            "effective_model": None,
            "cost_available": False,
        })
        return result

    async def embed(self, texts, **kwargs):
        raise NotImplementedError("Hermes API server embeddings are not supported; select an embedding provider")


class NVIDIAProvider(BaseLLMProvider):
    """NVIDIA API provider (Nemotron, Llama, etc.)."""

    def __init__(self, api_key: str, model: str = "nemotron-3-ultra"):
        super().__init__(
            api_key=api_key,
            model=model,
            base_url="https://integrate.api.nvidia.com/v1",
            input_cost_per_1k=0.0004,  # Nemotron pricing (approx)
            output_cost_per_1k=0.0004,
        )

    @property
    def name(self) -> str:
        return "nvidia"

    async def complete(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> LLMResponse:
        client = await self._get_client()

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        # NVIDIA supports response_format for some models
        if response_format and self.model in ["nemotron-3-ultra", "nemotron-4-340b"]:
            payload["response_format"] = response_format

        payload.update({k: v for k, v in kwargs.items() if v is not None})

        response = await client.post(f"{self.base_url}/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        input_tokens, output_tokens = self._parse_usage(data)
        cost = self.estimate_cost(input_tokens, output_tokens)

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost_usd=cost,
            model=self.model,
            provider=self.name,
            metadata={"finish_reason": data["choices"][0].get("finish_reason")},
        )

    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        client = await self._get_client()

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        async with client.stream("POST", f"{self.base_url}/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    async def embed(
        self,
        texts: List[str],
        **kwargs,
    ) -> List[List[float]]:
        client = await self._get_client()

        # NVIDIA embedding models
        embed_model = kwargs.get("model", "nvidia/embedding-v1")

        payload = {
            "model": embed_model,
            "input": texts,
            "input_type": "passage",
        }

        response = await client.post(f"{self.base_url}/embeddings", json=payload)
        response.raise_for_status()
        data = response.json()

        return [item["embedding"] for item in data["data"]]


class LLMClient:
    """Main LLM client with provider management and controlled fallback."""

    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._default_provider: Optional[str] = None
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize available providers from settings."""
        # OpenAI
        if settings.OPENAI_API_KEY:
            self._providers["openai"] = OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
            )
            if self._default_provider is None:
                self._default_provider = "openai"

        # NVIDIA
        if settings.NVIDIA_API_KEY:
            self._providers["nvidia"] = NVIDIAProvider(
                api_key=settings.NVIDIA_API_KEY,
                model=settings.NVIDIA_MODEL,
            )
            if self._default_provider is None:
                self._default_provider = "nvidia"

        # Hermes is opt-in and never becomes the implicit default.
        if settings.HERMES_BASE_URL and settings.HERMES_API_KEY:
            self._providers["hermes"] = HermesProvider(
                api_key=settings.HERMES_API_KEY,
                model=settings.HERMES_MODEL,
                base_url=settings.HERMES_BASE_URL,
            )

        # Override default from settings
        if settings.DEFAULT_LLM_PROVIDER in self._providers:
            self._default_provider = settings.DEFAULT_LLM_PROVIDER

    def get_provider(self, provider_name: Optional[str] = None) -> LLMProvider:
        """Get provider by name or default."""
        name = provider_name or self._default_provider
        if name is None:
            raise ValueError("No LLM provider configured. Set OPENAI_API_KEY or NVIDIA_API_KEY.")
        if name not in self._providers:
            raise ValueError(f"Provider '{name}' not available. Available: {list(self._providers.keys())}")
        return self._providers[name]

    @property
    def default_provider(self) -> Optional[str]:
        return self._default_provider

    @property
    def available_providers(self) -> List[str]:
        return list(self._providers.keys())

    async def complete(
        self,
        messages: List[LLMMessage],
        provider: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        fallback: Optional[bool] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Complete with controlled fallback.

        Args:
            fallback: If True, try other providers on failure.
                     Defaults to settings.LLM_FALLBACK_ENABLED (default False).
        """
        provider_name = provider or self._default_provider
        if not provider_name:
            raise ValueError("No provider specified and no default configured")

        # Use settings default for fallback if not explicitly provided
        use_fallback = settings.LLM_FALLBACK_ENABLED if fallback is None else fallback

        last_error = None
        providers_to_try = [provider_name]

        if use_fallback:
            # Add other providers as fallback
            for p in self._providers:
                if p != provider_name:
                    providers_to_try.append(p)

        for p_name in providers_to_try:
            try:
                provider_instance = self.get_provider(p_name)
                response = await provider_instance.complete(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    **kwargs,
                )
                # The successful adapter is determined by this dispatch, not by
                # requested provider or any value in model-generated text.
                response.provider = p_name
                return response
            except Exception as e:
                last_error = e
                continue

        raise last_error or RuntimeError("All providers failed")

    async def embed(
        self,
        texts: List[str],
        provider: Optional[str] = None,
        **kwargs,
    ) -> List[List[float]]:
        """Generate embeddings."""
        provider_instance = self.get_provider(provider)
        return await provider_instance.embed(texts, **kwargs)

    async def close(self) -> None:
        """Close all provider connections."""
        for provider in self._providers.values():
            if hasattr(provider, "close"):
                await provider.close()


# Global client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create global LLM client."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


async def close_llm_client() -> None:
    """Close global LLM client."""
    global _llm_client
    if _llm_client:
        await _llm_client.close()
        _llm_client = None