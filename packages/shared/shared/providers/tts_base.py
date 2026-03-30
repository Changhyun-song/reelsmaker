"""Abstract base for TTS (Text-to-Speech) providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WordTimestamp:
    """Single word timing for subtitle sync."""
    word: str
    start_ms: int
    end_ms: int


@dataclass
class TTSRequest:
    text: str
    voice_id: str = "default"
    language: str = "ko"
    speed: float = 1.0
    emotion: str = ""
    speaker_name: str = ""
    model: str | None = None
    output_format: str = "mp3"
    provider_options: dict[str, Any] = field(default_factory=dict)


@dataclass
class TTSResponse:
    audio_bytes: bytes
    duration_ms: int
    sample_rate: int = 44100
    mime_type: str = "audio/mpeg"
    word_timestamps: list[WordTimestamp] = field(default_factory=list)
    model: str = ""
    provider: str = ""
    latency_ms: int = 0
    cost_estimate: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class TTSProvider(ABC):
    """Abstract base for all TTS providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def generate(self, request: TTSRequest) -> TTSResponse:
        """Generate audio from text. Returns raw bytes + timing data."""
        ...

    @abstractmethod
    async def list_voices(self) -> list[dict[str, str]]:
        """Return available voices: [{"id": ..., "name": ..., "language": ...}]."""
        ...

    @abstractmethod
    async def health_check(self) -> bool: ...
