"""Still image motion presets for Ken Burns and similar effects.

Provides diverse motion patterns mapped to camera movement hints,
shot types, and pacing zones.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MotionPreset:
    """A named image motion configuration."""
    name: str
    label: str
    effect: str = "ken_burns"
    zoom_start: float = 1.0
    zoom_end: float = 1.15
    pan_direction: str = "center"
    easing: str = "linear"  # "linear" | "ease_in" | "ease_out" | "ease_in_out"
    params: dict = field(default_factory=dict)


SLOW_ZOOM_IN = MotionPreset(
    name="slow_zoom_in", label="Slow Zoom In",
    zoom_start=1.0, zoom_end=1.2, pan_direction="center",
    easing="ease_in_out",
)

SLOW_ZOOM_OUT = MotionPreset(
    name="slow_zoom_out", label="Slow Zoom Out",
    zoom_start=1.25, zoom_end=1.0, pan_direction="center",
    easing="ease_in_out",
)

GENTLE_PAN_RIGHT = MotionPreset(
    name="gentle_pan_right", label="Gentle Pan Right",
    zoom_start=1.08, zoom_end=1.12, pan_direction="left_to_right",
    easing="linear",
)

GENTLE_PAN_LEFT = MotionPreset(
    name="gentle_pan_left", label="Gentle Pan Left",
    zoom_start=1.08, zoom_end=1.12, pan_direction="right_to_left",
    easing="linear",
)

TILT_UP = MotionPreset(
    name="tilt_up", label="Tilt Up",
    zoom_start=1.05, zoom_end=1.1, pan_direction="bottom_to_top",
    easing="ease_out",
)

TILT_DOWN = MotionPreset(
    name="tilt_down", label="Tilt Down",
    zoom_start=1.05, zoom_end=1.1, pan_direction="top_to_bottom",
    easing="ease_out",
)

DRAMATIC_ZOOM_IN = MotionPreset(
    name="dramatic_zoom_in", label="Dramatic Zoom In",
    zoom_start=1.0, zoom_end=1.4, pan_direction="center",
    easing="ease_in",
)

PUSH_IN_LEFT = MotionPreset(
    name="push_in_left", label="Push In (Left Focus)",
    zoom_start=1.0, zoom_end=1.25, pan_direction="right_to_left",
    easing="ease_in_out",
)

PUSH_IN_RIGHT = MotionPreset(
    name="push_in_right", label="Push In (Right Focus)",
    zoom_start=1.0, zoom_end=1.25, pan_direction="left_to_right",
    easing="ease_in_out",
)

PULL_BACK = MotionPreset(
    name="pull_back", label="Pull Back / Reveal",
    zoom_start=1.35, zoom_end=1.0, pan_direction="center",
    easing="ease_out",
)

STATIC_HOLD = MotionPreset(
    name="static_hold", label="Static (Minimal Motion)",
    zoom_start=1.0, zoom_end=1.02, pan_direction="center",
    easing="linear",
)

HOOK_ZOOM = MotionPreset(
    name="hook_zoom", label="Hook Impact Zoom",
    zoom_start=1.0, zoom_end=1.35, pan_direction="center",
    easing="ease_in",
)

_PRESETS: dict[str, MotionPreset] = {
    p.name: p for p in [
        SLOW_ZOOM_IN, SLOW_ZOOM_OUT,
        GENTLE_PAN_RIGHT, GENTLE_PAN_LEFT,
        TILT_UP, TILT_DOWN,
        DRAMATIC_ZOOM_IN, PUSH_IN_LEFT, PUSH_IN_RIGHT, PULL_BACK,
        STATIC_HOLD, HOOK_ZOOM,
    ]
}

_CAMERA_MOTION_MAP: dict[str, str] = {
    "zoom in": "slow_zoom_in",
    "zoom_in": "slow_zoom_in",
    "zoom out": "slow_zoom_out",
    "zoom_out": "slow_zoom_out",
    "dolly in": "slow_zoom_in",
    "dolly out": "pull_back",
    "dolly_in": "slow_zoom_in",
    "dolly_out": "pull_back",
    "pan left": "gentle_pan_left",
    "pan_left": "gentle_pan_left",
    "pan right": "gentle_pan_right",
    "pan_right": "gentle_pan_right",
    "tilt up": "tilt_up",
    "tilt_up": "tilt_up",
    "tilt down": "tilt_down",
    "tilt_down": "tilt_down",
    "push in": "push_in_right",
    "push_in": "push_in_right",
    "pull back": "pull_back",
    "pull_back": "pull_back",
    "static": "static_hold",
    "truck left": "gentle_pan_left",
    "truck right": "gentle_pan_right",
}

_ZONE_DEFAULTS: dict[str, list[str]] = {
    "hook": ["hook_zoom", "dramatic_zoom_in", "push_in_right"],
    "body": ["slow_zoom_in", "gentle_pan_right", "gentle_pan_left", "tilt_up"],
    "climax": ["dramatic_zoom_in", "push_in_left", "slow_zoom_out"],
    "outro": ["slow_zoom_out", "pull_back", "static_hold"],
}


def get_motion_preset(name: str) -> MotionPreset:
    return _PRESETS.get(name.lower(), SLOW_ZOOM_IN)


def resolve_image_motion(
    camera_movement: str | None = None,
    shot_type: str | None = None,
    zone: str = "body",
    shot_index: int = 0,
) -> MotionPreset:
    """Pick the best motion preset from camera movement hint, shot type, and zone.

    Uses the camera_movement string first, then falls back to zone-based
    cycling to ensure visual variety.
    """
    if camera_movement:
        cam = camera_movement.lower().strip()
        for keyword, preset_name in _CAMERA_MOTION_MAP.items():
            if keyword in cam:
                return get_motion_preset(preset_name)

    zone_pool = _ZONE_DEFAULTS.get(zone, _ZONE_DEFAULTS["body"])
    chosen_name = zone_pool[shot_index % len(zone_pool)]
    return get_motion_preset(chosen_name)
