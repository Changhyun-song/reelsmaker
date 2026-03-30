"""ElevenLabs TTS provider — high-quality multilingual text-to-speech."""

from __future__ import annotations

import logging
import time
from typing import Any

from shared.providers.tts_base import (
    TTSProvider,
    TTSRequest,
    TTSResponse,
    WordTimestamp,
)

logger = logging.getLogger("reelsmaker.providers.elevenlabs")

_OUTPUT_FORMAT = "mp3_44100_128"


def _estimate_word_timestamps(text: str, duration_ms: int) -> list[WordTimestamp]:
    """Fallback word-level timestamps by proportional character distribution."""
    words = text.split()
    if not words or duration_ms <= 0:
        return []

    total_chars = max(sum(len(w) for w in words), 1)
    timestamps: list[WordTimestamp] = []
    cursor = 0
    for w in words:
        word_dur = max(int(duration_ms * len(w) / total_chars), 50)
        timestamps.append(WordTimestamp(word=w, start_ms=cursor, end_ms=min(cursor + word_dur, duration_ms)))
        cursor += word_dur
    if timestamps:
        timestamps[-1].end_ms = duration_ms
    return timestamps


class ElevenLabsTTSProvider(TTSProvider):
    """Generate speech using ElevenLabs API.

    Requires ELEVENLABS_API_KEY environment variable.
    Default model: eleven_multilingual_v2 (supports Korean).
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "eleven_multilingual_v2",
        default_voice_id: str = "",
        timeout_sec: int = 60,
    ):
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY is required for ElevenLabsTTSProvider")
        self._api_key = api_key
        self._default_model = default_model
        self._default_voice_id = default_voice_id
        self._timeout = timeout_sec

    @property
    def provider_name(self) -> str:
        return "elevenlabs"

    async def generate(self, request: TTSRequest) -> TTSResponse:
        try:
            from elevenlabs.client import ElevenLabs
        except ImportError as exc:
            raise ImportError("elevenlabs package required: pip install elevenlabs") from exc

        model = request.model or self._default_model
        voice_id = request.voice_id
        if not voice_id or voice_id.startswith("narrator-"):
            voice_id = self._default_voice_id or "21m00Tcm4TlvDq8ikWAM"  # "Rachel" fallback

        start = time.monotonic()

        client = ElevenLabs(api_key=self._api_key)

        voice_settings: dict[str, Any] = {}
        if request.speed != 1.0:
            voice_settings["speed"] = request.speed

        generation = client.text_to_speech.convert(
            text=request.text,
            voice_id=voice_id,
            model_id=model,
            output_format=_OUTPUT_FORMAT,
        )

        audio_chunks: list[bytes] = []
        for chunk in generation:
            audio_chunks.append(chunk)
        audio_bytes = b"".join(audio_chunks)

        latency_ms = int((time.monotonic() - start) * 1000)

        duration_ms = self._estimate_audio_duration(audio_bytes)

        word_timestamps = _estimate_word_timestamps(request.text, duration_ms)

        logger.info(
            "elevenlabs generate: voice=%s model=%s duration=%dms latency=%dms size=%dKB",
            voice_id, model, duration_ms, latency_ms, len(audio_bytes) // 1024,
        )

        return TTSResponse(
            audio_bytes=audio_bytes,
            duration_ms=duration_ms,
            sample_rate=44100,
            mime_type="audio/mpeg",
            word_timestamps=word_timestamps,
            model=model,
            provider="elevenlabs",
            latency_ms=latency_ms,
            cost_estimate=len(request.text) * 0.00003,
            metadata={
                "voice_id": voice_id,
                "language": request.language,
                "speed": request.speed,
                "text_length": len(request.text),
                "output_format": _OUTPUT_FORMAT,
            },
        )

    def _estimate_audio_duration(self, mp3_bytes: bytes) -> int:
        """Estimate MP3 duration from file size (128kbps → 16KB/sec)."""
        if not mp3_bytes:
            return 0
        bytes_per_ms = (128 * 1000 / 8) / 1000  # 128kbps → bytes per ms
        return max(int(len(mp3_bytes) / bytes_per_ms), 100)

    async def list_voices(self) -> list[dict[str, str]]:
        try:
            from elevenlabs.client import ElevenLabs
        except ImportError:
            return []

        try:
            client = ElevenLabs(api_key=self._api_key)
            response = client.voices.get_all()
            return [
                {
                    "id": v.voice_id,
                    "name": v.name,
                    "language": ",".join(
                        getattr(v, "labels", {}).get("language", "unknown")
                        if isinstance(getattr(v, "labels", {}), dict)
                        else "unknown"
                    ),
                }
                for v in response.voices[:50]
            ]
        except Exception as exc:
            logger.warning("Failed to list ElevenLabs voices: %s", exc)
            return []

    async def health_check(self) -> bool:
        try:
            from elevenlabs.client import ElevenLabs
            client = ElevenLabs(api_key=self._api_key)
            client.voices.get_all()
            return True
        except Exception:
            return False
