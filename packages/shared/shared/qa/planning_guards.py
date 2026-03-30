"""Semantic quality guards for AI planning stages.

Each ``validate_*_semantic`` function receives a parsed Pydantic model and
returns a list of human-readable error strings.  An empty list means the
output passed all semantic checks.

These guards catch problems that pass JSON schema validation but produce
vague/generic content that degrades downstream image/video quality.
"""

from __future__ import annotations

import re
from typing import Any

# ── Banned phrase lists (case-insensitive matching) ───

GENERIC_OPENERS = [
    "오늘은", "안녕하세요", "hi everyone", "in this video",
    "welcome to", "hey guys", "what's up", "hello and welcome",
    "today we", "let me show", "여러분",
]

GENERIC_VISUAL_NOTES = [
    "relevant image", "show example", "적절한 영상", "관련 이미지",
    "relevant visuals", "good visuals", "nice visuals", "appropriate visuals",
    "show the product", "적절한 이미지", "관련 영상",
]

GENERIC_SETTINGS = [
    "an office", "a room", "somewhere", "nice place", "a place",
    "some location", "relevant location", "a studio", "a space",
    "a building", "background", "indoors", "outdoors",
]

GENERIC_SUBJECTS = [
    "a person", "someone", "the subject", "the character",
    "a man", "a woman", "people", "the host", "the presenter",
    "a figure", "an individual",
]

VAGUE_LIGHTING_TERMS = [
    "good lighting", "nice lighting", "well-lit", "beautiful lighting",
    "proper lighting", "natural lighting", "studio lighting",
]

VAGUE_DESCRIPTORS = [
    "beautiful shot", "nice background", "good composition",
    "aesthetic", "beautiful scene", "amazing visual", "stunning",
    "gorgeous", "lovely", "pretty",
]

# visual_notes format: must contain shot-type bracket and at least one of Lighting/Camera
_VISUAL_NOTES_PATTERN = re.compile(
    r"\[.+?\].*(?:lighting|camera|lens|angle|color)",
    re.IGNORECASE,
)


def _contains_any(text: str, phrases: list[str]) -> str | None:
    """Return the first matching banned phrase found, or None."""
    low = text.lower().strip()
    for p in phrases:
        if p.lower() in low:
            return p
    return None


def _word_count(text: str) -> int:
    return len(text.split())


# ── 1. Script Plan Guards ────────────────────────────


def validate_script_plan_semantic(plan: Any) -> list[str]:
    """Validate a ScriptPlanOutput for semantic quality."""
    errors: list[str] = []

    hook = getattr(plan, "hook", "") or ""
    match = _contains_any(hook, GENERIC_OPENERS)
    if match:
        errors.append(
            f"Hook starts with generic opener '{match}'. "
            "Use a surprising stat, provocative question, or bold claim instead."
        )

    sections = getattr(plan, "sections", []) or []
    for i, sec in enumerate(sections):
        vn = getattr(sec, "visual_notes", "") or ""
        if len(vn) < 30:
            errors.append(
                f"Section[{i}].visual_notes is too short ({len(vn)} chars). "
                "Need ≥30 chars with shot type, subject, lighting, and camera details."
            )

        if len(vn) >= 10 and not _VISUAL_NOTES_PATTERN.search(vn):
            errors.append(
                f"Section[{i}].visual_notes lacks required format. "
                "Use: '[Shot type] Subject doing action in environment. "
                "Lighting: X. Camera: Y.'"
            )

        gm = _contains_any(vn, GENERIC_VISUAL_NOTES)
        if gm:
            errors.append(
                f"Section[{i}].visual_notes contains generic phrase '{gm}'. "
                "Describe specific visuals a cinematographer could execute."
            )

        gm = _contains_any(vn, VAGUE_DESCRIPTORS)
        if gm:
            errors.append(
                f"Section[{i}].visual_notes contains vague descriptor '{gm}'. "
                "Replace with concrete visual details."
            )

    draft = getattr(plan, "narration_draft", "") or ""
    narration_parts = [getattr(s, "narration", "") for s in sections]
    if narration_parts and draft:
        combined_len = sum(len(p) for p in narration_parts)
        draft_len = len(draft)
        if combined_len > 0 and abs(draft_len - combined_len) / combined_len > 0.5:
            errors.append(
                "narration_draft length deviates >50% from concatenated section narrations. "
                "The draft should be the sections joined with natural transitions."
            )

    return errors


# ── 2. Scene Breakdown Guards ────────────────────────


def validate_scene_breakdown_semantic(output: Any) -> list[str]:
    """Validate a SceneBreakdownOutput for semantic quality."""
    errors: list[str] = []

    scenes = getattr(output, "scenes", []) or []

    for i, scene in enumerate(scenes):
        setting = getattr(scene, "setting", "") or ""
        gm = _contains_any(setting, GENERIC_SETTINGS)
        if gm:
            errors.append(
                f"Scene[{i}].setting is generic ('{gm}'). "
                "Specify concrete details: materials, lighting conditions, key objects, "
                "time of day. E.g. 'modern minimalist home office, white desk, "
                "single monitor, afternoon sunlight through blinds'."
            )

        vi = getattr(scene, "visual_intent", "") or ""
        if len(vi) < 30:
            errors.append(
                f"Scene[{i}].visual_intent is too short ({len(vi)} chars). "
                "Need ≥30 chars with color palette, camera style, and key visual elements."
            )

        has_color = bool(re.search(
            r"(warm|cool|cold|neutral|blue|teal|gold|amber|orange|red|green|"
            r"pastel|saturated|muted|monochrome|\d{4}K|kelvin)",
            vi, re.IGNORECASE,
        ))
        has_object = _word_count(vi) >= 6
        if len(vi) >= 15 and not (has_color and has_object):
            errors.append(
                f"Scene[{i}].visual_intent is too abstract. "
                "Include specific color temperature/palette AND key visual objects/movements."
            )

        gm = _contains_any(vi, VAGUE_DESCRIPTORS)
        if gm:
            errors.append(
                f"Scene[{i}].visual_intent contains vague descriptor '{gm}'. "
                "Replace with concrete visual direction."
            )

    for i in range(1, len(scenes)):
        prev_mood = (getattr(scenes[i - 1], "mood", "") or "").lower()
        curr_mood = (getattr(scenes[i], "mood", "") or "").lower()
        transition = (getattr(scenes[i - 1], "transition_hint", "") or "").lower()

        calm_words = {"calm", "peaceful", "serene", "gentle", "relaxed", "quiet", "soft"}
        intense_words = {"intense", "urgent", "dramatic", "explosive", "tense", "chaotic", "fierce"}

        prev_calm = any(w in prev_mood for w in calm_words)
        curr_intense = any(w in curr_mood for w in intense_words)
        prev_intense = any(w in prev_mood for w in intense_words)
        curr_calm = any(w in curr_mood for w in calm_words)

        if (prev_calm and curr_intense) or (prev_intense and curr_calm):
            if transition in ("cut", "smash_cut", ""):
                errors.append(
                    f"Scene[{i-1}]→Scene[{i}] has extreme mood shift "
                    f"('{prev_mood}' → '{curr_mood}') with abrupt transition '{transition}'. "
                    "Use dissolve/fade or add transitional beat in narration."
                )

    return errors


# ── 3. Shot Breakdown Guards ─────────────────────────


def validate_shot_breakdown_semantic(output: Any) -> list[str]:
    """Validate a ShotBreakdownOutput for semantic quality."""
    errors: list[str] = []

    shots = getattr(output, "shots", []) or []

    for i, shot in enumerate(shots):
        desc = getattr(shot, "description", "") or ""
        if len(desc) < 60:
            errors.append(
                f"Shot[{i}].description is too short ({len(desc)} chars, need ≥60). "
                "Must include: subject + action/pose + environment + lighting + mood."
            )

        required_elements = {
            "subject/action": bool(re.search(
                r"(person|woman|man|hand|figure|object|product|screen|device|item|character|people|worker|developer|host|presenter|speaker|child|team|group)",
                desc, re.IGNORECASE,
            )),
            "environment/setting": bool(re.search(
                r"(room|office|desk|studio|outdoor|street|kitchen|background|"
                r"interior|exterior|wall|floor|table|window|space|scene|setting)",
                desc, re.IGNORECASE,
            )),
            "lighting/mood": bool(re.search(
                r"(light|shadow|glow|bright|dark|warm|cool|cinematic|mood|"
                r"ambient|soft|harsh|golden|dramatic|natural|lamp|sun|neon)",
                desc, re.IGNORECASE,
            )),
        }
        missing = [k for k, v in required_elements.items() if not v]
        if len(desc) >= 30 and missing:
            errors.append(
                f"Shot[{i}].description missing elements: {', '.join(missing)}. "
                "A complete prompt needs subject, environment, and lighting/mood."
            )

        subj = getattr(shot, "subject", "") or ""
        gm = _contains_any(subj, GENERIC_SUBJECTS)
        if gm:
            errors.append(
                f"Shot[{i}].subject is generic ('{gm}'). "
                "Be specific: age, clothing, distinguishing features. "
                "E.g. 'woman in navy blazer holding tablet' not 'a person'."
            )

    # Check for 3+ consecutive identical camera_framing
    framings = [getattr(s, "camera_framing", "") for s in shots]
    for i in range(len(framings) - 2):
        if framings[i] and framings[i] == framings[i + 1] == framings[i + 2]:
            errors.append(
                f"Shots [{i}]-[{i+2}] use identical camera_framing '{framings[i]}' "
                "3 times consecutively. Vary framing for visual rhythm."
            )

    # Check narration coverage balance (compare each to average of others)
    segments = [len(getattr(s, "narration_segment", "") or "") for s in shots]
    if len(segments) >= 3 and sum(segments) > 0:
        for i, seg_len in enumerate(segments):
            others = [s for j, s in enumerate(segments) if j != i]
            others_avg = sum(others) / len(others) if others else 0
            if others_avg > 0 and seg_len > others_avg * 5:
                errors.append(
                    f"Shot[{i}].narration_segment is disproportionately long "
                    f"({seg_len} chars vs others avg {others_avg:.0f}). "
                    "Redistribute narration more evenly across shots."
                )
            elif sum(segments) > 0 and seg_len / sum(segments) > 0.7 and len(segments) >= 3:
                errors.append(
                    f"Shot[{i}].narration_segment holds {seg_len/sum(segments):.0%} "
                    f"of total narration. Redistribute more evenly across shots."
                )

    return errors


# ── 4. Frame Spec Guards ─────────────────────────────


_LIGHTING_ROLE_PATTERN = re.compile(
    r"(key|fill|rim|accent|back|edge|hair|kicker)",
    re.IGNORECASE,
)

_PHYSICAL_POSE_PATTERN = re.compile(
    r"(hand|arm|leg|head|shoulder|lean|sit|stand|hold|grip|touch|point|"
    r"reach|turn|twist|bend|cross|fold|raise|lower|gesture|tilt|gaze|"
    r"rest|curl|stretch|crouch|kneel|recline|finger|wrist|elbow|torso)",
    re.IGNORECASE,
)


def validate_frame_spec_semantic(output: Any) -> list[str]:
    """Validate a FrameSpecOutput for semantic quality."""
    errors: list[str] = []

    frames = getattr(output, "frames", []) or []

    for i, frame in enumerate(frames):
        role = getattr(frame, "frame_role", "")

        lighting = getattr(frame, "lighting", "") or ""
        light_roles = _LIGHTING_ROLE_PATTERN.findall(lighting)
        unique_roles = set(r.lower() for r in light_roles)
        if len(unique_roles) < 2:
            errors.append(
                f"Frame[{i}]({role}).lighting has {len(unique_roles)} lighting role(s), "
                "need ≥2 (e.g. key + fill, or key + rim). "
                "Describe direction, color temperature, and role for each light."
            )

        gm = _contains_any(lighting, VAGUE_LIGHTING_TERMS)
        if gm:
            errors.append(
                f"Frame[{i}]({role}).lighting contains vague term '{gm}'. "
                "Specify direction (camera-left 45°), temperature (3200K/5600K), "
                "and role (key/fill/rim)."
            )

        pose = getattr(frame, "action_pose", "") or ""
        if pose and not _PHYSICAL_POSE_PATTERN.search(pose):
            errors.append(
                f"Frame[{i}]({role}).action_pose lacks physical posture description. "
                "Include body part positioning (hands, shoulders, head angle), "
                "not just emotions like 'happy' or 'focused'."
            )

        bg = getattr(frame, "background_description", "") or ""
        layer_words = re.findall(
            r"(foreground|immediate|mid|middle|far|distant|backdrop|behind|front)",
            bg, re.IGNORECASE,
        )
        if len(bg) >= 15 and len(set(w.lower() for w in layer_words)) < 2:
            errors.append(
                f"Frame[{i}]({role}).background_description lacks depth layers. "
                "Describe at least 2 of: foreground, mid-ground, far background."
            )

    # Check start vs end frame similarity when motion != static
    start_frame = None
    end_frame = None
    for f in frames:
        r = getattr(f, "frame_role", "")
        if r == "start":
            start_frame = f
        elif r == "end":
            end_frame = f

    if start_frame and end_frame:
        s_comp = (getattr(start_frame, "composition", "") or "").lower()
        e_comp = (getattr(end_frame, "composition", "") or "").lower()
        s_pos = (getattr(start_frame, "subject_position", "") or "").lower()
        e_pos = (getattr(end_frame, "subject_position", "") or "").lower()

        if s_comp and e_comp and s_comp == e_comp and s_pos == e_pos:
            errors.append(
                "Start and end frames have identical composition and subject_position. "
                "If camera has motion, frames must reflect positional change. "
                "If static, at least vary the action_pose/expression subtly."
            )

    return errors
