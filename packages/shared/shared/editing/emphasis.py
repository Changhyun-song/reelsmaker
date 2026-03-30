"""Subtitle emphasis rules — keyword highlighting, hook formatting.

Supports SRT/ASS-style formatting for burned-in subtitles:
  - Bold/italic markers for key phrases
  - Hook text special styling
  - Number/stat emphasis
  - Question emphasis
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class EmphasisRule:
    name: str
    pattern: str  # regex
    style: str  # "bold" | "italic" | "color" | "highlight" | "size_up"
    color: str | None = None  # hex, e.g. "FFFF00" (yellow, in BGR for ASS)
    priority: int = 0


DEFAULT_EMPHASIS_RULES: list[EmphasisRule] = [
    EmphasisRule(
        name="number_stat",
        pattern=r"\d+[\d,.]*[%배만억천원달러$€]",
        style="bold",
        priority=10,
    ),
    EmphasisRule(
        name="quoted_phrase",
        pattern=r'["\u201c\u201d]([^"\u201c\u201d]+)["\u201c\u201d]',
        style="italic",
        priority=5,
    ),
    EmphasisRule(
        name="question_mark",
        pattern=r"[^\s]+\?",
        style="bold",
        priority=3,
    ),
    EmphasisRule(
        name="exclamation",
        pattern=r"[^\s]+!",
        style="bold",
        priority=2,
    ),
    EmphasisRule(
        name="parenthetical",
        pattern=r"\(([^)]+)\)",
        style="italic",
        priority=1,
    ),
]

HOOK_EMPHASIS_RULES: list[EmphasisRule] = [
    EmphasisRule(
        name="hook_number",
        pattern=r"\d+[\d,.]*[%배만억천원달러$€]?",
        style="bold",
        color="00FFFF",  # cyan in BGR for ASS
        priority=15,
    ),
    EmphasisRule(
        name="hook_question",
        pattern=r"[^\s]+\?",
        style="bold",
        color="00FFFF",
        priority=12,
    ),
]


def _apply_srt_bold(text: str, match_start: int, match_end: int) -> str:
    return text[:match_start] + "<b>" + text[match_start:match_end] + "</b>" + text[match_end:]


def _apply_srt_italic(text: str, match_start: int, match_end: int) -> str:
    return text[:match_start] + "<i>" + text[match_start:match_end] + "</i>" + text[match_end:]


def apply_emphasis(
    text: str,
    rules: list[EmphasisRule] | None = None,
    is_hook: bool = False,
    style_format: str = "srt",
) -> str:
    """Apply emphasis markers to subtitle text.

    For SRT: uses <b>, <i> tags (supported by most players and ffmpeg subtitles filter).
    Returns the text with inline formatting tags.
    """
    if not text or not text.strip():
        return text

    active_rules = list(rules or DEFAULT_EMPHASIS_RULES)
    if is_hook:
        active_rules = HOOK_EMPHASIS_RULES + active_rules

    active_rules.sort(key=lambda r: -r.priority)

    marked_ranges: list[tuple[int, int]] = []

    result = text
    offset = 0

    for rule in active_rules:
        try:
            for m in re.finditer(rule.pattern, text):
                ms, me = m.start(), m.end()
                if any(ms < er and me > sr for sr, er in marked_ranges):
                    continue
                marked_ranges.append((ms, me))

                adj_start = ms + offset
                adj_end = me + offset

                if style_format == "srt":
                    if rule.style == "bold":
                        before = result
                        result = result[:adj_start] + "<b>" + result[adj_start:adj_end] + "</b>" + result[adj_end:]
                        offset += len(result) - len(before)
                    elif rule.style == "italic":
                        before = result
                        result = result[:adj_start] + "<i>" + result[adj_start:adj_end] + "</i>" + result[adj_end:]
                        offset += len(result) - len(before)

        except re.error:
            continue

    return result


def apply_korean_line_breaks(
    text: str,
    max_chars: int = 35,
    prefer_particle_break: bool = True,
) -> str:
    """Smart Korean line breaking that respects grammatical particles.

    Prefers breaking after particles (은/는/이/가/을/를/에/에서/로/으로/와/과/도/만)
    rather than splitting mid-phrase.
    """
    if len(text) <= max_chars:
        return text

    particles = [
        "에서는", "에서", "으로는", "으로", "에는", "에게",
        "는", "은", "이", "가", "을", "를", "에", "로",
        "와", "과", "도", "만", "의", "라", "며", "고",
    ]

    words = text.split()
    if len(words) <= 1:
        return text

    best_break = len(text) // 2
    best_score = 999

    cursor = 0
    for i, word in enumerate(words):
        cursor += len(word) + (1 if i > 0 else 0)
        if cursor < 5 or cursor > len(text) - 5:
            continue

        balance = abs(cursor - len(text) / 2)

        particle_bonus = 0
        if prefer_particle_break:
            for p in particles:
                if word.endswith(p):
                    particle_bonus = -10
                    break

        score = balance + particle_bonus
        if score < best_score:
            best_score = score
            best_break = cursor

    line1 = text[:best_break].rstrip()
    line2 = text[best_break:].lstrip()

    return f"{line1}\n{line2}"
