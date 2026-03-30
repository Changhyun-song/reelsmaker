"""Mock TTS provider — generates a minimal valid MP3 silence for flow testing.

Produces word-level timestamps by simple character-length estimation.
"""

from __future__ import annotations

import struct
import time

from shared.providers.tts_base import (
    TTSProvider,
    TTSRequest,
    TTSResponse,
    WordTimestamp,
)

# Precomputed minimal MP3 frame (MPEG1 Layer3, 128kbps, 44100Hz, silence)
_MP3_SILENCE_FRAME = bytes([
    0xFF, 0xFB, 0x90, 0x00,  # header
]) + b'\x00' * 413  # padding to 417 bytes (one frame at 128kbps/44100)


def _generate_silence_mp3(duration_ms: int) -> bytes:
    """Generate a silent MP3 of approximately the given duration."""
    frames_per_sec = 44100 / 1152  # ~38.28 frames/sec for MPEG1 Layer3
    num_frames = max(1, int(frames_per_sec * duration_ms / 1000))
    return _MP3_SILENCE_FRAME * num_frames


def _estimate_word_timestamps(text: str, duration_ms: int) -> list[WordTimestamp]:
    """Estimate word-level timestamps by proportional character distribution."""
    words = text.split()
    if not words:
        return []

    total_chars = sum(len(w) for w in words)
    if total_chars == 0:
        return []

    timestamps: list[WordTimestamp] = []
    cursor_ms = 0
    for w in words:
        word_dur = int(duration_ms * len(w) / total_chars)
        word_dur = max(word_dur, 50)
        timestamps.append(WordTimestamp(
            word=w,
            start_ms=cursor_ms,
            end_ms=min(cursor_ms + word_dur, duration_ms),
        ))
        cursor_ms += word_dur

    if timestamps:
        timestamps[-1].end_ms = duration_ms

    return timestamps


def _estimate_duration_ms(text: str, speed: float) -> int:
    """Rough estimation: ~150ms per Korean syllable, ~80ms per latin char."""
    dur = 0
    for ch in text:
        if '\uac00' <= ch <= '\ud7a3':
            dur += 150
        elif ch.isalpha():
            dur += 80
        elif ch == ' ':
            dur += 50
        else:
            dur += 30
    return max(500, int(dur / max(speed, 0.5)))


MOCK_VOICES = [
    {"id": "narrator-ko-male", "name": "한국어 남성 내레이터", "language": "ko"},
    {"id": "narrator-ko-female", "name": "한국어 여성 내레이터", "language": "ko"},
    {"id": "narrator-en-male", "name": "English Male Narrator", "language": "en"},
    {"id": "narrator-en-female", "name": "English Female Narrator", "language": "en"},
]


class MockTTSProvider(TTSProvider):
    """Generates silent MP3 with word timestamps for flow testing."""

    @property
    def provider_name(self) -> str:
        return "mock_tts"

    async def generate(self, request: TTSRequest) -> TTSResponse:
        start = time.monotonic()

        duration_ms = _estimate_duration_ms(request.text, request.speed)
        audio_bytes = _generate_silence_mp3(duration_ms)
        word_timestamps = _estimate_word_timestamps(request.text, duration_ms)

        elapsed = int((time.monotonic() - start) * 1000)

        return TTSResponse(
            audio_bytes=audio_bytes,
            duration_ms=duration_ms,
            sample_rate=44100,
            mime_type="audio/mpeg",
            word_timestamps=word_timestamps,
            model="mock-tts",
            provider="mock_tts",
            latency_ms=elapsed,
            cost_estimate=0.0,
            metadata={
                "voice_id": request.voice_id,
                "language": request.language,
                "speed": request.speed,
                "text_length": len(request.text),
                "word_count": len(request.text.split()),
            },
        )

    async def list_voices(self) -> list[dict[str, str]]:
        return MOCK_VOICES

    async def health_check(self) -> bool:
        return True
