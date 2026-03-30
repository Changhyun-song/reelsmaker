"""Abstract base for image generation providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ImageGenerationRequest:
    prompt: str
    negative_prompt: str = ""
    width: int = 1920
    height: int = 1080
    num_variants: int = 1
    model: str | None = None
    seed: int | None = None
    guidance_scale: float | None = None
    provider_options: dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedImage:
    """Single generated image result."""
    image_bytes: bytes
    width: int
    height: int
    mime_type: str = "image/png"
    seed: int | None = None
    variant_index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageGenerationResponse:
    images: list[GeneratedImage]
    model: str = ""
    provider: str = ""
    latency_ms: int = 0
    cost_estimate: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ImageProvider(ABC):
    """Abstract base for all image generation providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """Generate image(s) from prompt. Returns raw bytes for each variant."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""
        ...
