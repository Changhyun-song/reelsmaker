"""Editing rules — format-specific pacing, transitions, motion, and emphasis.

These are pure-function rule engines used by the timeline composer and renderer.
"""

from shared.editing.pacing import (
    FormatProfile,
    PacingRule,
    get_format_profile,
    get_pacing_rules,
)
from shared.editing.transitions import (
    TransitionPreset,
    get_transition_preset,
    resolve_transition,
)
from shared.editing.motion import (
    MotionPreset,
    get_motion_preset,
    resolve_image_motion,
)
from shared.editing.emphasis import (
    EmphasisRule,
    apply_emphasis,
)

__all__ = [
    "FormatProfile",
    "PacingRule",
    "get_format_profile",
    "get_pacing_rules",
    "TransitionPreset",
    "get_transition_preset",
    "resolve_transition",
    "MotionPreset",
    "get_motion_preset",
    "resolve_image_motion",
    "EmphasisRule",
    "apply_emphasis",
]
