from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderRequest:
    system_prompt: str
    user_prompt: str
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    response_format: str = "json"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderResponse:
    content: str
    parsed: dict | None = None
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


class ProviderError(Exception):
    """Raised when a provider call fails."""

    def __init__(
        self,
        message: str,
        provider: str = "",
        retryable: bool = False,
    ):
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class TextProvider(ABC):
    """Abstract base for all text-generation AI providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def generate(self, request: ProviderRequest) -> ProviderResponse: ...
