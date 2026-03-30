"""Timing resolver for subtitle segments.

Supports two sources:
  - "tts": Word-level timestamps from VoiceTrack.timestamps
  - "estimated": Character-length-based estimation (fallback)

Designed to accept future "forced_alignment" source.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WordTiming:
    word: str
    start_ms: int
    end_ms: int


@dataclass
class ShotNarration:
    """Input: one shot's narration with optional TTS timing."""
    shot_id: str
    text: str
    order_index: int
    duration_sec: float | None = None
    word_timestamps: list[WordTiming] | None = None
    speaker: str | None = None


def _estimate_char_duration_ms(ch: str) -> int:
    """Per-character duration estimate for fallback timing."""
    if '\uac00' <= ch <= '\ud7a3':
        return 140
    if ch.isalpha():
        return 70
    if ch == ' ':
        return 40
    return 25


def estimate_word_timings(
    text: str,
    offset_ms: int = 0,
    total_duration_ms: int | None = None,
) -> list[WordTiming]:
    """Generate estimated word timings from text length proportions."""
    words = text.split()
    if not words:
        return []

    raw_durations = []
    for w in words:
        raw_durations.append(sum(_estimate_char_duration_ms(c) for c in w))

    raw_total = sum(raw_durations)
    if raw_total == 0:
        return []

    if total_duration_ms and total_duration_ms > 0:
        scale = total_duration_ms / raw_total
    else:
        scale = 1.0

    timings: list[WordTiming] = []
    cursor = offset_ms
    for w, raw_dur in zip(words, raw_durations):
        dur = max(50, int(raw_dur * scale))
        timings.append(WordTiming(word=w, start_ms=cursor, end_ms=cursor + dur))
        cursor += dur

    return timings


def resolve_timing(
    narrations: list[ShotNarration],
    gap_between_shots_ms: int = 200,
) -> tuple[list[WordTiming], str]:
    """Resolve word-level timings for all shots, returning (timings, source).

    Returns:
        (all_word_timings, timing_source)
        timing_source: "tts" if all had TTS, "estimated" if any used fallback, "mixed" if partial
    """
    all_timings: list[WordTiming] = []
    cursor_ms = 0
    has_tts = 0
    has_estimated = 0

    sorted_narrations = sorted(narrations, key=lambda n: n.order_index)

    for narr in sorted_narrations:
        if not narr.text or not narr.text.strip():
            continue

        if narr.word_timestamps:
            has_tts += 1
            for wt in narr.word_timestamps:
                all_timings.append(WordTiming(
                    word=wt.word,
                    start_ms=cursor_ms + wt.start_ms,
                    end_ms=cursor_ms + wt.end_ms,
                ))
            if narr.word_timestamps:
                cursor_ms += narr.word_timestamps[-1].end_ms + gap_between_shots_ms
        else:
            has_estimated += 1
            shot_dur_ms = int((narr.duration_sec or 4.0) * 1000) if narr.duration_sec else None
            word_timings = estimate_word_timings(
                narr.text.strip(), offset_ms=cursor_ms, total_duration_ms=shot_dur_ms,
            )
            all_timings.extend(word_timings)
            if word_timings:
                cursor_ms = word_timings[-1].end_ms + gap_between_shots_ms

    if has_tts > 0 and has_estimated == 0:
        source = "tts"
    elif has_tts == 0:
        source = "estimated"
    else:
        source = "mixed"

    return all_timings, source
