"""Format-specific pacing rules.

Defines rhythm, beat insertion, hook handling, and scene transition
timing for different video formats (shorts, explainer, product_ad, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PacingRule:
    """Describes how a specific segment of the video should be paced."""
    zone: str  # "hook" | "body" | "climax" | "outro"
    max_shot_duration_ms: int = 8000
    min_shot_duration_ms: int = 1500
    preferred_shot_duration_ms: int = 4000
    cut_rhythm: str = "steady"  # "rapid" | "steady" | "slow" | "varied"
    pause_after_scene_ms: int = 0
    pause_after_hook_ms: int = 0
    beat_marker_ms: int = 0  # micro-pause for emphasis


@dataclass(frozen=True)
class FormatProfile:
    """Complete pacing profile for a video format."""
    name: str
    label: str
    target_fps: int = 30
    default_transition: str = "cut"
    hook_duration_sec: float = 3.0
    hook_rules: PacingRule = field(default_factory=lambda: PacingRule(zone="hook"))
    body_rules: PacingRule = field(default_factory=lambda: PacingRule(zone="body"))
    climax_rules: PacingRule = field(default_factory=lambda: PacingRule(zone="climax"))
    outro_rules: PacingRule = field(default_factory=lambda: PacingRule(zone="outro"))
    scene_gap_ms: int = 300
    scene_transition: str = "dip_to_black"
    intro_fade_in_ms: int = 0
    outro_fade_out_ms: int = 0
    subtitle_style: str = "default"


SHORTS_PROFILE = FormatProfile(
    name="shorts",
    label="YouTube Shorts / Reels",
    hook_duration_sec=2.5,
    hook_rules=PacingRule(
        zone="hook",
        max_shot_duration_ms=2500,
        min_shot_duration_ms=800,
        preferred_shot_duration_ms=1500,
        cut_rhythm="rapid",
        pause_after_hook_ms=200,
    ),
    body_rules=PacingRule(
        zone="body",
        max_shot_duration_ms=5000,
        min_shot_duration_ms=1500,
        preferred_shot_duration_ms=3000,
        cut_rhythm="varied",
        beat_marker_ms=100,
    ),
    climax_rules=PacingRule(
        zone="climax",
        max_shot_duration_ms=4000,
        min_shot_duration_ms=1000,
        preferred_shot_duration_ms=2000,
        cut_rhythm="rapid",
    ),
    outro_rules=PacingRule(
        zone="outro",
        max_shot_duration_ms=6000,
        min_shot_duration_ms=2000,
        preferred_shot_duration_ms=4000,
        cut_rhythm="slow",
    ),
    scene_gap_ms=150,
    scene_transition="cut",
    intro_fade_in_ms=300,
    outro_fade_out_ms=500,
    subtitle_style="bold_hook",
)

EXPLAINER_PROFILE = FormatProfile(
    name="explainer",
    label="Explainer / Educational",
    hook_duration_sec=4.0,
    hook_rules=PacingRule(
        zone="hook",
        max_shot_duration_ms=4000,
        min_shot_duration_ms=1500,
        preferred_shot_duration_ms=2500,
        cut_rhythm="steady",
        pause_after_hook_ms=400,
    ),
    body_rules=PacingRule(
        zone="body",
        max_shot_duration_ms=8000,
        min_shot_duration_ms=2500,
        preferred_shot_duration_ms=5000,
        cut_rhythm="steady",
        beat_marker_ms=200,
        pause_after_scene_ms=500,
    ),
    climax_rules=PacingRule(
        zone="climax",
        max_shot_duration_ms=6000,
        min_shot_duration_ms=2000,
        preferred_shot_duration_ms=4000,
        cut_rhythm="steady",
    ),
    outro_rules=PacingRule(
        zone="outro",
        max_shot_duration_ms=8000,
        min_shot_duration_ms=3000,
        preferred_shot_duration_ms=5000,
        cut_rhythm="slow",
    ),
    scene_gap_ms=500,
    scene_transition="dip_to_black",
    intro_fade_in_ms=500,
    outro_fade_out_ms=800,
    subtitle_style="default",
)

PRODUCT_AD_PROFILE = FormatProfile(
    name="product_ad",
    label="Product Ad / Commercial",
    hook_duration_sec=2.0,
    hook_rules=PacingRule(
        zone="hook",
        max_shot_duration_ms=2000,
        min_shot_duration_ms=600,
        preferred_shot_duration_ms=1200,
        cut_rhythm="rapid",
        pause_after_hook_ms=100,
    ),
    body_rules=PacingRule(
        zone="body",
        max_shot_duration_ms=4000,
        min_shot_duration_ms=1000,
        preferred_shot_duration_ms=2500,
        cut_rhythm="varied",
        beat_marker_ms=80,
    ),
    climax_rules=PacingRule(
        zone="climax",
        max_shot_duration_ms=3000,
        min_shot_duration_ms=800,
        preferred_shot_duration_ms=1500,
        cut_rhythm="rapid",
    ),
    outro_rules=PacingRule(
        zone="outro",
        max_shot_duration_ms=5000,
        min_shot_duration_ms=2000,
        preferred_shot_duration_ms=3000,
        cut_rhythm="steady",
    ),
    scene_gap_ms=100,
    scene_transition="crossfade",
    intro_fade_in_ms=200,
    outro_fade_out_ms=600,
    subtitle_style="minimal",
)

EMOTIONAL_PROFILE = FormatProfile(
    name="emotional_narration",
    label="Emotional Narration / Story",
    hook_duration_sec=5.0,
    hook_rules=PacingRule(
        zone="hook",
        max_shot_duration_ms=6000,
        min_shot_duration_ms=2000,
        preferred_shot_duration_ms=4000,
        cut_rhythm="slow",
        pause_after_hook_ms=600,
    ),
    body_rules=PacingRule(
        zone="body",
        max_shot_duration_ms=8000,
        min_shot_duration_ms=3000,
        preferred_shot_duration_ms=5000,
        cut_rhythm="slow",
        beat_marker_ms=300,
        pause_after_scene_ms=800,
    ),
    climax_rules=PacingRule(
        zone="climax",
        max_shot_duration_ms=6000,
        min_shot_duration_ms=2000,
        preferred_shot_duration_ms=4000,
        cut_rhythm="steady",
    ),
    outro_rules=PacingRule(
        zone="outro",
        max_shot_duration_ms=10000,
        min_shot_duration_ms=3000,
        preferred_shot_duration_ms=6000,
        cut_rhythm="slow",
    ),
    scene_gap_ms=800,
    scene_transition="dip_to_black",
    intro_fade_in_ms=800,
    outro_fade_out_ms=1200,
    subtitle_style="cinematic",
)

_PROFILES: dict[str, FormatProfile] = {
    "shorts": SHORTS_PROFILE,
    "explainer": EXPLAINER_PROFILE,
    "product_ad": PRODUCT_AD_PROFILE,
    "emotional_narration": EMOTIONAL_PROFILE,
}


def get_format_profile(format_name: str | None) -> FormatProfile:
    """Get a format profile by name, defaulting to shorts."""
    if not format_name:
        return SHORTS_PROFILE
    return _PROFILES.get(format_name.lower(), SHORTS_PROFILE)


def get_pacing_rules(profile: FormatProfile, zone: str) -> PacingRule:
    """Get pacing rules for a specific zone within a format."""
    mapping = {
        "hook": profile.hook_rules,
        "body": profile.body_rules,
        "climax": profile.climax_rules,
        "outro": profile.outro_rules,
    }
    return mapping.get(zone, profile.body_rules)


def classify_shot_zone(
    shot_index: int,
    total_shots: int,
    elapsed_ms: int,
    total_duration_ms: int,
    profile: FormatProfile,
) -> str:
    """Determine which pacing zone a shot belongs to."""
    hook_ms = int(profile.hook_duration_sec * 1000)

    if elapsed_ms < hook_ms:
        return "hook"

    if total_shots <= 2:
        return "body"

    remaining_ratio = 1.0 - (elapsed_ms / max(total_duration_ms, 1))
    if remaining_ratio <= 0.15:
        return "outro"

    progress = elapsed_ms / max(total_duration_ms, 1)
    if 0.6 <= progress <= 0.85:
        return "climax"

    return "body"
