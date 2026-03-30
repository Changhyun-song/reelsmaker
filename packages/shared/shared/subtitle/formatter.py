"""SRT and VTT formatters for subtitle cues."""

from __future__ import annotations

from shared.subtitle.segmenter import SubtitleCue


def _ms_to_srt_time(ms: int) -> str:
    """Convert milliseconds to SRT timecode: HH:MM:SS,mmm"""
    if ms < 0:
        ms = 0
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    mi = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{mi:03d}"


def _ms_to_vtt_time(ms: int) -> str:
    """Convert milliseconds to VTT timecode: HH:MM:SS.mmm"""
    return _ms_to_srt_time(ms).replace(",", ".")


def segments_to_srt(cues: list[SubtitleCue]) -> str:
    """Format subtitle cues as SRT string."""
    lines: list[str] = []
    for cue in cues:
        lines.append(str(cue.index + 1))
        lines.append(f"{_ms_to_srt_time(cue.start_ms)} --> {_ms_to_srt_time(cue.end_ms)}")
        lines.append(cue.text)
        lines.append("")
    return "\n".join(lines)


def segments_to_vtt(cues: list[SubtitleCue]) -> str:
    """Format subtitle cues as WebVTT string."""
    lines: list[str] = ["WEBVTT", ""]
    for cue in cues:
        lines.append(str(cue.index + 1))
        lines.append(f"{_ms_to_vtt_time(cue.start_ms)} --> {_ms_to_vtt_time(cue.end_ms)}")
        lines.append(cue.text)
        lines.append("")
    return "\n".join(lines)
