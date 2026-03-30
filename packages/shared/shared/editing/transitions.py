"""Transition presets and resolution logic.

Provides named transition presets with ffmpeg-compatible parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TransitionPreset:
    """A named transition effect."""
    name: str
    label: str
    type: str  # ffmpeg xfade type or custom keyword
    duration_ms: int = 500
    params: dict = field(default_factory=dict)
    ffmpeg_xfade_name: str | None = None


CUT = TransitionPreset(
    name="cut", label="Cut", type="cut", duration_ms=0,
)

CROSSFADE = TransitionPreset(
    name="crossfade", label="Crossfade",
    type="xfade", duration_ms=500,
    ffmpeg_xfade_name="fade",
)

DIP_TO_BLACK = TransitionPreset(
    name="dip_to_black", label="Dip to Black",
    type="custom_dip", duration_ms=400,
    params={"fade_out_ms": 200, "black_ms": 0, "fade_in_ms": 200},
)

DISSOLVE = TransitionPreset(
    name="dissolve", label="Dissolve",
    type="xfade", duration_ms=600,
    ffmpeg_xfade_name="dissolve",
)

FADE_IN = TransitionPreset(
    name="fade_in", label="Fade In",
    type="fade_in", duration_ms=500,
)

FADE_OUT = TransitionPreset(
    name="fade_out", label="Fade Out",
    type="fade_out", duration_ms=500,
)

WIPE_LEFT = TransitionPreset(
    name="wipe_left", label="Wipe Left",
    type="xfade", duration_ms=400,
    ffmpeg_xfade_name="wipeleft",
)

WIPE_RIGHT = TransitionPreset(
    name="wipe_right", label="Wipe Right",
    type="xfade", duration_ms=400,
    ffmpeg_xfade_name="wiperight",
)

SLIDE_LEFT = TransitionPreset(
    name="slide_left", label="Slide Left",
    type="xfade", duration_ms=400,
    ffmpeg_xfade_name="slideleft",
)

SLIDE_RIGHT = TransitionPreset(
    name="slide_right", label="Slide Right",
    type="xfade", duration_ms=400,
    ffmpeg_xfade_name="slideright",
)

ZOOM_IN_TRANSITION = TransitionPreset(
    name="zoom_in", label="Zoom Transition",
    type="xfade", duration_ms=400,
    ffmpeg_xfade_name="smoothup",
)

_PRESETS: dict[str, TransitionPreset] = {
    p.name: p for p in [
        CUT, CROSSFADE, DIP_TO_BLACK, DISSOLVE,
        FADE_IN, FADE_OUT,
        WIPE_LEFT, WIPE_RIGHT, SLIDE_LEFT, SLIDE_RIGHT,
        ZOOM_IN_TRANSITION,
    ]
}


def get_transition_preset(name: str) -> TransitionPreset:
    return _PRESETS.get(name.lower(), CUT)


def resolve_transition(
    hint: str | None,
    scene_boundary: bool = False,
    is_first: bool = False,
    is_last: bool = False,
    format_default: str = "cut",
    scene_default: str = "dip_to_black",
) -> TransitionPreset:
    """Resolve a transition from a shot hint string plus context.

    Priority: explicit hint > scene boundary default > format default.
    First/last shots get fade_in/fade_out if enabled.
    """
    if is_first:
        return get_transition_preset("fade_in")

    if is_last:
        return get_transition_preset("fade_out")

    if hint:
        h = hint.lower().strip()
        for preset_name, preset in _PRESETS.items():
            if preset_name in h or preset.label.lower() in h:
                return preset
        for keyword in ("dissolve", "fade", "wipe", "slide", "zoom", "cross"):
            if keyword in h:
                matched = next(
                    (p for p in _PRESETS.values() if keyword in p.name),
                    None,
                )
                if matched:
                    return matched

    if scene_boundary:
        return get_transition_preset(scene_default)

    return get_transition_preset(format_default)
