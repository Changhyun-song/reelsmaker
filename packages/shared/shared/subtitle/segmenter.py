"""Subtitle segmenter — groups word timings into display-ready subtitle cues.

v2: Korean-aware line breaking, emphasis markers, hook formatting.

Applies rules:
  - max_chars_per_line: soft limit for line width
  - max_lines: lines per subtitle cue (typically 2)
  - min_segment_ms / max_segment_ms: duration bounds
  - gap_ms: minimum gap between consecutive cues
  - emphasis: bold/italic markers on numbers, questions, hook text
  - korean_line_break: smart breaks at grammatical particle boundaries
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.editing.emphasis import apply_emphasis, apply_korean_line_breaks
from shared.subtitle.timing import WordTiming


@dataclass
class SubtitleCue:
    index: int
    start_ms: int
    end_ms: int
    text: str
    shot_id: str | None = None
    speaker: str | None = None
    is_hook: bool = False
    pacing_zone: str = "body"


@dataclass
class SegmenterConfig:
    max_chars_per_line: int = 35
    max_lines: int = 2
    gap_ms: int = 100
    min_segment_ms: int = 500
    max_segment_ms: int = 6000
    line_break_strategy: str = "korean"  # "word" | "korean"
    enable_emphasis: bool = True
    hook_duration_ms: int = 3000


def _wrap_text(words: list[str], max_chars: int, max_lines: int, strategy: str = "word") -> str:
    """Word-wrap a list of words into max_lines, each <= max_chars."""
    raw = " ".join(words)

    if strategy == "korean":
        return apply_korean_line_breaks(raw, max_chars=max_chars)

    lines: list[str] = []
    current_line = ""

    for w in words:
        test = f"{current_line} {w}".strip() if current_line else w
        if len(test) > max_chars and current_line:
            lines.append(current_line)
            current_line = w
            if len(lines) >= max_lines:
                break
        else:
            current_line = test

    if current_line and len(lines) < max_lines:
        lines.append(current_line)

    return "\n".join(lines)


def build_segments(
    word_timings: list[WordTiming],
    config: SegmenterConfig | None = None,
) -> list[SubtitleCue]:
    """Group word timings into subtitle cues respecting line/duration constraints."""
    if not word_timings:
        return []

    cfg = config or SegmenterConfig()
    max_chars_total = cfg.max_chars_per_line * cfg.max_lines

    cues: list[SubtitleCue] = []
    buf_words: list[str] = []
    buf_start_ms: int | None = None
    buf_end_ms: int = 0
    buf_char_count = 0

    def flush() -> None:
        nonlocal buf_words, buf_start_ms, buf_end_ms, buf_char_count
        if not buf_words or buf_start_ms is None:
            return

        text = _wrap_text(buf_words, cfg.max_chars_per_line, cfg.max_lines, cfg.line_break_strategy)
        dur = buf_end_ms - buf_start_ms
        if dur < cfg.min_segment_ms:
            buf_end_ms = buf_start_ms + cfg.min_segment_ms

        is_hook = buf_start_ms < cfg.hook_duration_ms
        zone = "hook" if is_hook else "body"

        if cfg.enable_emphasis:
            text = apply_emphasis(text, is_hook=is_hook, style_format="srt")

        cues.append(SubtitleCue(
            index=len(cues),
            start_ms=buf_start_ms,
            end_ms=buf_end_ms,
            text=text,
            is_hook=is_hook,
            pacing_zone=zone,
        ))
        buf_words = []
        buf_start_ms = None
        buf_end_ms = 0
        buf_char_count = 0

    for wt in word_timings:
        word_chars = len(wt.word) + (1 if buf_words else 0)
        dur_if_added = (wt.end_ms - (buf_start_ms or wt.start_ms))

        should_flush = False
        if buf_char_count + word_chars > max_chars_total:
            should_flush = True
        if dur_if_added > cfg.max_segment_ms and buf_words:
            should_flush = True

        if should_flush:
            flush()

        if buf_start_ms is None:
            buf_start_ms = wt.start_ms
        buf_words.append(wt.word)
        buf_end_ms = wt.end_ms
        buf_char_count += word_chars

    flush()

    # Apply gap between cues
    for i in range(1, len(cues)):
        prev_end = cues[i - 1].end_ms
        this_start = cues[i].start_ms
        if this_start - prev_end < cfg.gap_ms:
            cues[i - 1].end_ms = max(cues[i - 1].start_ms + cfg.min_segment_ms,
                                      this_start - cfg.gap_ms)

    for i, cue in enumerate(cues):
        cue.index = i

    return cues
