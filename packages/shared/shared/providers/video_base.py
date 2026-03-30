"""Abstract base for video generation providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VideoGenerationRequest:
    """Input for video generation.

    Supports two modes:
      - image_to_video: provide start_frame_bytes (and optionally end_frame_bytes)
      - text_to_video:  provide prompt only (no frame bytes)
    """
    prompt: str
    negative_prompt: str = ""
    mode: str = "image_to_video"  # "image_to_video" | "text_to_video"
    start_frame_bytes: bytes | None = None
    start_frame_mime: str = "image/png"
    end_frame_bytes: bytes | None = None
    end_frame_mime: str = "image/png"
    duration_sec: float = 4.0
    width: int = 1920
    height: int = 1080
    aspect_ratio: str = "16:9"
    fps: int = 24
    model: str | None = None
    seed: int | None = None
    provider_options: dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedVideo:
    """Single generated video result."""
    video_bytes: bytes
    width: int
    height: int
    duration_sec: float
    fps: int = 24
    mime_type: str = "video/mp4"
    seed: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VideoGenerationResponse:
    video: GeneratedVideo
    model: str = ""
    provider: str = ""
    latency_ms: int = 0
    cost_estimate: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class VideoProvider(ABC):
    """Abstract base for all video generation providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        """Generate a short video clip. Returns raw bytes."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""
        ...
