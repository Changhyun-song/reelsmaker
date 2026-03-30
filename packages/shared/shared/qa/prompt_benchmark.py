"""Text-only prompt quality benchmark.

Scores planning outputs and compiled prompts on four axes:
  1. Specificity   — concrete subject/action/environment/lighting/camera/lens/background/mood
  2. Continuity    — style anchor, lighting direction, subject identity lock
  3. Motion clarity — camera_motion-aligned language in start/end/video prompts
  4. Artifact prevention — negative prompt coverage and forbidden elements

Each axis is scored 0–100. The overall score is a weighted average.
All scoring is deterministic and reproducible (no AI calls).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ── Score weights ────────────────────────────────────

_WEIGHTS = {
    "specificity": 0.35,
    "continuity": 0.20,
    "motion_clarity": 0.20,
    "artifact_prevention": 0.25,
}

_MAX_FAILURE_REASONS = 10

# ── Keyword / pattern banks ──────────────────────────

_SUBJECT_PATTERNS = re.compile(
    r"(person|woman|man|child|figure|hand|hands|face|body|"
    r"character|host|presenter|speaker|object|product|device|"
    r"screen|icon|app|phone|laptop|headphone|earphone|earbuds|"
    r"worker|developer|team|group|couple|model|artist)",
    re.IGNORECASE,
)

_ACTION_PATTERNS = re.compile(
    r"(typing|walking|running|holding|speaking|looking|pointing|"
    r"gestur|lean|sitting|standing|reaching|scrolling|tapping|"
    r"waving|smiling|reading|writing|touching|pressing|lifting|"
    r"placing|pour|cooking|dancing|stretching|listening)",
    re.IGNORECASE,
)

_ENVIRONMENT_PATTERNS = re.compile(
    r"(room|office|studio|outdoor|street|café|kitchen|desk|"
    r"table|window|wall|floor|park|city|skyline|mountain|"
    r"interior|exterior|corridor|stage|rooftop|garden|"
    r"bedroom|bathroom|library|classroom|workspace|store)",
    re.IGNORECASE,
)

_LIGHTING_PATTERNS = re.compile(
    r"(light|shadow|glow|bright|dark|warm|cool|ambient|"
    r"lamp|sun|neon|rim|key|fill|backlight|edge|spotlight|"
    r"\d{4}K|kelvin|golden.hour|blue.hour|overcast|"
    r"candlelight|fluorescent|silhouette|chiaroscuro)",
    re.IGNORECASE,
)

_CAMERA_PATTERNS = re.compile(
    r"(close.up|medium|wide|extreme|overhead|low.angle|"
    r"bird|dutch|eye.level|high.angle|aerial|top.down)",
    re.IGNORECASE,
)

_LENS_PATTERNS = re.compile(
    r"(\d+mm|f/\d|focal|shallow|deep.focus|bokeh|"
    r"anamorphic|telephoto|wide.angle|macro|portrait.lens|"
    r"tilt.shift|DOF|depth.of.field)",
    re.IGNORECASE,
)

_BACKGROUND_PATTERNS = re.compile(
    r"(background|foreground|mid.ground|distant|backdrop|"
    r"behind|front|layer|depth|far|near|blurred.back)",
    re.IGNORECASE,
)

_MOOD_PATTERNS = re.compile(
    r"(mood|emotion|tone|feeling|atmosphere|vibe|"
    r"tense|calm|energetic|melanchol|nostalgic|hopeful|"
    r"dramatic|serene|urgent|contemplat|joyful|somber|"
    r"cinematic|intimate|epic|playful|mysterious|peaceful)",
    re.IGNORECASE,
)

# Continuity detection
_STYLE_ANCHOR_PATTERNS = re.compile(
    r"(STYLE.ANCHOR|style.consistency|rendering.style|"
    r"cinematic|film.grain|anime|watercolor|photo.?realistic|"
    r"minimalist|infographic|3D.render|illustration)",
    re.IGNORECASE,
)

_IDENTITY_LOCK_PATTERNS = re.compile(
    r"(CHARACTER.LOCK|identity|same.person|consistent.appearance|"
    r"forbidden.change|forbidden.drift|always.with|signature|"
    r"must.not.change|maintain.identity)",
    re.IGNORECASE,
)

_LIGHTING_DIRECTION_PATTERNS = re.compile(
    r"(camera.left|camera.right|above|below|behind|"
    r"from.left|from.right|overhead|side|front|"
    r"45°|90°|top.down|back.?light|rim|edge)",
    re.IGNORECASE,
)

# Motion language
_MOTION_LANGUAGE = {
    "static": re.compile(
        r"(static|still|subtle|no.motion|hold|micro.expression|minimal.movement)",
        re.IGNORECASE,
    ),
    "pan": re.compile(
        r"(pan|lateral|reveal|slide|sweep|horizontal.move)",
        re.IGNORECASE,
    ),
    "dolly": re.compile(
        r"(dolly|push|approach|closer|recede|pull.back|physically.move)",
        re.IGNORECASE,
    ),
    "zoom": re.compile(
        r"(zoom|tighter|wider.framing|focal.length|no.parallax)",
        re.IGNORECASE,
    ),
    "tracking": re.compile(
        r"(track|follow|alongside|parallax|spatial)",
        re.IGNORECASE,
    ),
    "orbit": re.compile(
        r"(orbit|rotate|around|circle|revolve)",
        re.IGNORECASE,
    ),
    "crane": re.compile(
        r"(crane|rise|descend|vertical|ascend)",
        re.IGNORECASE,
    ),
    "tilt": re.compile(
        r"(tilt|upward|downward|vertical.pan)",
        re.IGNORECASE,
    ),
    "handheld": re.compile(
        r"(handheld|organic|shake|documentary|raw)",
        re.IGNORECASE,
    ),
}

# Artifact prevention baseline terms
_IMAGE_NEGATIVE_EXPECTED = {
    "text", "watermark", "logo", "blurry", "extra fingers",
    "extra limbs", "bad anatomy", "deformed face",
}
_VIDEO_NEGATIVE_EXPECTED = {
    "temporal flicker", "frame jitter", "morphing face",
    "warped hands", "rubber limbs", "compression artifacts",
}


# ── Data classes ─────────────────────────────────────


@dataclass
class BenchmarkScores:
    specificity: float = 0.0
    continuity: float = 0.0
    motion_clarity: float = 0.0
    artifact_prevention: float = 0.0
    overall: float = 0.0
    failure_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "specificity": round(self.specificity, 1),
            "continuity": round(self.continuity, 1),
            "motion_clarity": round(self.motion_clarity, 1),
            "artifact_prevention": round(self.artifact_prevention, 1),
            "overall": round(self.overall, 1),
            "failure_reasons": self.failure_reasons[:_MAX_FAILURE_REASONS],
        }


@dataclass
class BenchmarkInput:
    """Flexible input — all fields optional; missing fields get scored as 0."""
    script_plan: Any | None = None
    scene_breakdown: Any | None = None
    shot_breakdown: Any | None = None
    frame_spec: Any | None = None
    image_prompt: str = ""
    video_prompt: str = ""
    negative_prompt: str = ""
    negative_video_prompt: str = ""
    continuity_notes: str = ""


# ── Scoring helpers ──────────────────────────────────


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _regex_coverage(text: str, pattern: re.Pattern) -> bool:
    return bool(pattern.search(text))


def _count_unique_matches(text: str, pattern: re.Pattern) -> int:
    return len({m.lower() for m in pattern.findall(text)})


# ── Specificity scoring ─────────────────────────────


def _score_specificity(inp: BenchmarkInput) -> tuple[float, list[str]]:
    """Score 0-100 based on coverage of 8 signal categories across all inputs."""
    reasons: list[str] = []

    all_text = " ".join([
        inp.image_prompt,
        inp.video_prompt,
        _extract_shot_descriptions(inp.shot_breakdown),
        _extract_frame_texts(inp.frame_spec),
        _extract_scene_texts(inp.scene_breakdown),
        _extract_script_visual_notes(inp.script_plan),
    ])

    if not all_text.strip():
        reasons.append("No text content provided for specificity analysis")
        return 0.0, reasons

    checks = {
        "subject": (_SUBJECT_PATTERNS, 12.5),
        "action": (_ACTION_PATTERNS, 12.5),
        "environment": (_ENVIRONMENT_PATTERNS, 12.5),
        "lighting": (_LIGHTING_PATTERNS, 12.5),
        "camera": (_CAMERA_PATTERNS, 12.5),
        "lens": (_LENS_PATTERNS, 12.5),
        "background": (_BACKGROUND_PATTERNS, 12.5),
        "mood": (_MOOD_PATTERNS, 12.5),
    }

    score = 0.0
    for name, (pattern, weight) in checks.items():
        count = _count_unique_matches(all_text, pattern)
        if count == 0:
            reasons.append(f"Specificity: no {name} terms found across prompts")
            continue
        # 1 match = 50% of weight, 2 = 80%, 3+ = 100%
        ratio = min(1.0, 0.5 + 0.25 * (count - 1)) if count >= 1 else 0.0
        score += weight * ratio

    # Bonus: long detailed descriptions (image prompt > 200 chars)
    if len(inp.image_prompt) > 200:
        score = min(100, score + 5)
    if len(inp.image_prompt) > 400:
        score = min(100, score + 5)

    # Penalty: very short image prompt
    if 0 < len(inp.image_prompt) < 80:
        reasons.append(f"Specificity: image prompt very short ({len(inp.image_prompt)} chars)")
        score = max(0, score - 15)

    return _clamp(score), reasons


# ── Continuity scoring ──────────────────────────────


def _score_continuity(inp: BenchmarkInput) -> tuple[float, list[str]]:
    """Score 0-100 based on style anchoring, lighting consistency, identity locks."""
    reasons: list[str] = []

    all_text = " ".join([
        inp.image_prompt,
        inp.video_prompt,
        inp.continuity_notes,
        _extract_frame_texts(inp.frame_spec),
    ])

    if not all_text.strip():
        reasons.append("No text content for continuity analysis")
        return 0.0, reasons

    score = 0.0

    # 1. Style anchor presence (0-35)
    style_matches = _count_unique_matches(all_text, _STYLE_ANCHOR_PATTERNS)
    if style_matches == 0:
        reasons.append("Continuity: no style anchor or rendering style keywords found")
    else:
        score += min(35, 15 + 10 * style_matches)

    # 2. Lighting direction consistency (0-30)
    direction_matches = _count_unique_matches(all_text, _LIGHTING_DIRECTION_PATTERNS)
    if direction_matches == 0:
        reasons.append("Continuity: no lighting direction references found")
    else:
        score += min(30, 10 + 10 * direction_matches)

    # 3. Character identity lock (0-35)
    identity_matches = _count_unique_matches(all_text, _IDENTITY_LOCK_PATTERNS)
    if identity_matches == 0:
        # Less severe if no characters expected
        if inp.frame_spec or inp.continuity_notes:
            reasons.append("Continuity: no character identity lock markers found")
        score += 10  # baseline if nothing expected
    else:
        score += min(35, 15 + 10 * identity_matches)

    return _clamp(score), reasons


# ── Motion clarity scoring ──────────────────────────


def _score_motion_clarity(inp: BenchmarkInput) -> tuple[float, list[str]]:
    """Score 0-100 based on camera-motion-aligned language in video prompt / frames."""
    reasons: list[str] = []

    video_text = inp.video_prompt
    frame_text = _extract_frame_texts(inp.frame_spec)
    all_motion_text = f"{video_text} {frame_text}"

    if not all_motion_text.strip():
        reasons.append("No video prompt or frame specs for motion analysis")
        return 0.0, reasons

    # Detect what camera motion is specified
    detected_motion = _detect_camera_motion(inp)
    if not detected_motion:
        # If no motion specified, just check for any motion language
        has_any = any(p.search(all_motion_text) for p in _MOTION_LANGUAGE.values())
        if has_any:
            return 60.0, reasons
        reasons.append("Motion clarity: no camera motion specified and no motion language found")
        return 30.0, reasons

    score = 0.0

    # Check if the correct motion family language exists
    motion_family = _get_motion_family(detected_motion)
    family_pattern = _MOTION_LANGUAGE.get(motion_family)

    if family_pattern and family_pattern.search(all_motion_text):
        score += 50
    elif family_pattern:
        reasons.append(
            f"Motion clarity: camera_motion is '{detected_motion}' "
            f"but video prompt lacks '{motion_family}'-family language"
        )
        score += 10

    # Check for duration mention
    if re.search(r"(duration|seconds|\d+\.?\d*s\b)", all_motion_text, re.IGNORECASE):
        score += 15

    # Check for start/end frame differentiation
    if inp.frame_spec:
        frames = getattr(inp.frame_spec, "frames", []) or []
        start = next((f for f in frames if getattr(f, "frame_role", "") == "start"), None)
        end = next((f for f in frames if getattr(f, "frame_role", "") == "end"), None)
        if start and end:
            s_comp = (getattr(start, "composition", "") or "").strip().lower()
            e_comp = (getattr(end, "composition", "") or "").strip().lower()
            s_pos = (getattr(start, "subject_position", "") or "").strip().lower()
            e_pos = (getattr(end, "subject_position", "") or "").strip().lower()

            if detected_motion != "static":
                if s_comp != e_comp or s_pos != e_pos:
                    score += 20
                else:
                    reasons.append(
                        "Motion clarity: start/end frames are identical "
                        f"but camera_motion is '{detected_motion}'"
                    )
            else:
                score += 15  # static doesn't need difference
        else:
            reasons.append("Motion clarity: missing start or end frame")
    else:
        score += 10  # no frame spec to evaluate

    # General motion vocabulary richness
    motion_vocab = sum(
        1 for p in _MOTION_LANGUAGE.values() if p.search(all_motion_text)
    )
    score += min(15, motion_vocab * 5)

    return _clamp(score), reasons


# ── Artifact prevention scoring ─────────────────────


def _score_artifact_prevention(inp: BenchmarkInput) -> tuple[float, list[str]]:
    """Score 0-100 based on negative prompt coverage and forbidden elements."""
    reasons: list[str] = []

    neg_image = inp.negative_prompt.lower()
    neg_video = inp.negative_video_prompt.lower()
    frame_forbidden = _extract_forbidden_elements(inp.frame_spec)

    score = 0.0

    # 1. Image negative coverage (0-40)
    if not neg_image:
        reasons.append("Artifact prevention: no image negative prompt")
    else:
        hits = sum(1 for t in _IMAGE_NEGATIVE_EXPECTED if t in neg_image)
        ratio = hits / len(_IMAGE_NEGATIVE_EXPECTED)
        score += 40 * ratio
        if ratio < 0.5:
            reasons.append(
                f"Artifact prevention: image negative covers only "
                f"{hits}/{len(_IMAGE_NEGATIVE_EXPECTED)} baseline terms"
            )

    # 2. Video negative coverage (0-35)
    if not neg_video:
        if inp.video_prompt:
            reasons.append("Artifact prevention: video prompt exists but no video negative")
    else:
        hits = sum(1 for t in _VIDEO_NEGATIVE_EXPECTED if t in neg_video)
        ratio = hits / len(_VIDEO_NEGATIVE_EXPECTED)
        score += 35 * ratio
        if ratio < 0.5:
            reasons.append(
                f"Artifact prevention: video negative covers only "
                f"{hits}/{len(_VIDEO_NEGATIVE_EXPECTED)} baseline terms"
            )

    # 3. Forbidden elements in frame specs (0-15)
    if frame_forbidden:
        unique_forbidden = len(set(t.strip().lower() for t in frame_forbidden.split(",") if t.strip()))
        score += min(15, unique_forbidden * 5)
    else:
        if inp.frame_spec:
            reasons.append("Artifact prevention: no forbidden_elements in frame specs")

    # 4. Negative prompt richness beyond baseline (0-10)
    total_neg_tokens = len([
        t for t in (neg_image + " " + neg_video).split(",") if t.strip()
    ])
    if total_neg_tokens > 15:
        score += 10
    elif total_neg_tokens > 8:
        score += 5

    return _clamp(score), reasons


# ── Text extraction helpers ─────────────────────────


def _extract_shot_descriptions(shot_breakdown: Any | None) -> str:
    if not shot_breakdown:
        return ""
    shots = getattr(shot_breakdown, "shots", []) or []
    parts = []
    for s in shots:
        parts.append(getattr(s, "description", "") or "")
        parts.append(getattr(s, "subject", "") or "")
        parts.append(getattr(s, "environment", "") or "")
        parts.append(getattr(s, "emotion", "") or "")
    return " ".join(parts)


def _extract_frame_texts(frame_spec: Any | None) -> str:
    if not frame_spec:
        return ""
    frames = getattr(frame_spec, "frames", []) or []
    parts = []
    for f in frames:
        for attr in ["composition", "lighting", "action_pose",
                      "background_description", "mood", "camera_angle",
                      "lens_feel", "continuity_notes"]:
            parts.append(getattr(f, attr, "") or "")
    return " ".join(parts)


def _extract_scene_texts(scene_breakdown: Any | None) -> str:
    if not scene_breakdown:
        return ""
    scenes = getattr(scene_breakdown, "scenes", []) or []
    parts = []
    for s in scenes:
        parts.append(getattr(s, "setting", "") or "")
        parts.append(getattr(s, "visual_intent", "") or "")
        parts.append(getattr(s, "mood", "") or "")
    return " ".join(parts)


def _extract_script_visual_notes(script_plan: Any | None) -> str:
    if not script_plan:
        return ""
    sections = getattr(script_plan, "sections", []) or []
    return " ".join(getattr(s, "visual_notes", "") or "" for s in sections)


def _extract_forbidden_elements(frame_spec: Any | None) -> str:
    if not frame_spec:
        return ""
    frames = getattr(frame_spec, "frames", []) or []
    parts = [getattr(f, "forbidden_elements", "") or "" for f in frames]
    return ", ".join(p for p in parts if p)


def _detect_camera_motion(inp: BenchmarkInput) -> str:
    """Best-effort camera motion detection from shot_breakdown or video prompt."""
    if inp.shot_breakdown:
        shots = getattr(inp.shot_breakdown, "shots", []) or []
        for s in shots:
            m = getattr(s, "camera_motion", "") or ""
            if m and m != "static":
                return m
            m2 = getattr(s, "camera_movement", "") or ""
            if m2 and m2 != "static":
                return m2
        if shots:
            return getattr(shots[0], "camera_motion", "") or "static"

    if "dolly" in inp.video_prompt.lower():
        return "dolly_in"
    if "pan" in inp.video_prompt.lower():
        return "pan_right"
    if "zoom" in inp.video_prompt.lower():
        return "zoom_in"
    if "track" in inp.video_prompt.lower():
        return "tracking_forward"
    if "orbit" in inp.video_prompt.lower():
        return "orbit_left"
    return ""


def _get_motion_family(motion: str) -> str:
    """Map specific motion to its family for pattern matching."""
    m = motion.lower()
    if "pan" in m:
        return "pan"
    if "dolly" in m or "push" in m:
        return "dolly"
    if "zoom" in m:
        return "zoom"
    if "track" in m:
        return "tracking"
    if "orbit" in m:
        return "orbit"
    if "crane" in m:
        return "crane"
    if "tilt" in m:
        return "tilt"
    if "handheld" in m:
        return "handheld"
    return "static"


# ── Main entry point ────────────────────────────────


def run_prompt_benchmark(inp: BenchmarkInput) -> BenchmarkScores:
    """Run the full prompt quality benchmark and return normalized scores."""
    all_reasons: list[str] = []

    specificity, s_reasons = _score_specificity(inp)
    all_reasons.extend(s_reasons)

    continuity, c_reasons = _score_continuity(inp)
    all_reasons.extend(c_reasons)

    motion, m_reasons = _score_motion_clarity(inp)
    all_reasons.extend(m_reasons)

    artifact, a_reasons = _score_artifact_prevention(inp)
    all_reasons.extend(a_reasons)

    overall = (
        specificity * _WEIGHTS["specificity"]
        + continuity * _WEIGHTS["continuity"]
        + motion * _WEIGHTS["motion_clarity"]
        + artifact * _WEIGHTS["artifact_prevention"]
    )

    return BenchmarkScores(
        specificity=round(specificity, 1),
        continuity=round(continuity, 1),
        motion_clarity=round(motion, 1),
        artifact_prevention=round(artifact, 1),
        overall=round(overall, 1),
        failure_reasons=all_reasons[:_MAX_FAILURE_REASONS],
    )
