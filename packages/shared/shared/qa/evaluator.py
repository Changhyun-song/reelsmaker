"""Automatic quality evaluator — rule-based scoring (1-5) per criterion.

Operates on the same QAContext used by the QA rule engine.
Returns a dict of scores that can be stored in QualityReview.scores.
"""

from __future__ import annotations

from shared.qa.criteria import CRITERIA_KEYS, compute_weighted_average
from shared.qa.rules import QAContext


def _clamp(v: float, lo: float = 1.0, hi: float = 5.0) -> int:
    return max(int(lo), min(int(hi), round(v)))


def _score_script_quality(ctx: QAContext) -> int:
    """Score based on whether a script version exists with rich plan data."""
    if not ctx.script_version_id:
        return 1
    has_scenes = len(ctx.scenes) > 0
    has_narration = any(s.narration_text for s in ctx.scenes)
    has_duration = ctx.target_duration_sec is not None
    score = 2
    if has_scenes:
        score += 1
    if has_narration:
        score += 1
    if has_duration:
        score += 1
    return _clamp(score)


def _score_scene_structure(ctx: QAContext) -> int:
    if not ctx.scenes:
        return 1
    score = 3.0
    n = len(ctx.scenes)
    if n >= 3:
        score += 0.5
    if n >= 5:
        score += 0.5

    durations = [s.duration_estimate_sec or 0 for s in ctx.scenes]
    total = sum(durations)
    if ctx.target_duration_sec and total > 0:
        ratio = total / ctx.target_duration_sec
        if 0.85 <= ratio <= 1.15:
            score += 0.5
        elif ratio < 0.7 or ratio > 1.3:
            score -= 1.0

    all_have_narration = all(s.narration_text for s in ctx.scenes)
    if all_have_narration:
        score += 0.5

    return _clamp(score)


def _score_shot_quality(ctx: QAContext) -> int:
    if not ctx.scenes:
        return 1
    all_shots = [sh for sc in ctx.scenes for sh in sc.shots]
    if not all_shots:
        return 1

    score = 3.0
    total = len(all_shots)

    with_narration = sum(1 for s in all_shots if s.narration_segment)
    with_strategy = sum(1 for s in all_shots if s.asset_strategy)
    dur_ok = sum(1 for s in all_shots if s.duration_sec and 2 <= s.duration_sec <= 8)

    score += (with_narration / total) * 0.5
    score += (with_strategy / total) * 0.5
    score += (dur_ok / total) * 1.0

    return _clamp(score)


def _score_frame_specificity(ctx: QAContext) -> int:
    all_shots = [sh for sc in ctx.scenes for sh in sc.shots]
    if not all_shots:
        return 1

    total_frames = sum(len(sh.frame_specs) for sh in all_shots)
    if total_frames == 0:
        return 1

    score = 2.5
    shots_with_frames = sum(1 for sh in all_shots if sh.frame_specs)
    coverage = shots_with_frames / len(all_shots)
    score += coverage * 1.5

    shots_with_start = sum(
        1 for sh in all_shots
        if any(f.get("frame_role") == "start" for f in sh.frame_specs)
    )
    shots_with_end = sum(
        1 for sh in all_shots
        if any(f.get("frame_role") == "end" for f in sh.frame_specs)
    )
    start_end_coverage = (shots_with_start + shots_with_end) / (2 * len(all_shots))
    score += start_end_coverage * 1.0

    return _clamp(score)


def _score_style_consistency(ctx: QAContext) -> int:
    """Heuristic: more complete pipeline = better consistency potential."""
    all_shots = [sh for sc in ctx.scenes for sh in sc.shots]
    if not all_shots:
        return 1

    score = 3.0
    with_images = sum(1 for sh in all_shots if sh.image_assets)
    if with_images > 0:
        score += min(with_images / len(all_shots), 1.0) * 1.0

    with_videos = sum(1 for sh in all_shots if sh.video_assets)
    if with_videos > 0:
        score += min(with_videos / len(all_shots), 1.0) * 1.0

    return _clamp(score)


def _score_image_quality(ctx: QAContext) -> int:
    all_shots = [sh for sc in ctx.scenes for sh in sc.shots]
    if not all_shots:
        return 1

    total = len(all_shots)
    ready = sum(
        1 for sh in all_shots
        if any(a.get("status") == "ready" for a in sh.image_assets)
    )
    if ready == 0:
        return 1

    score = 2.0 + (ready / total) * 3.0
    return _clamp(score)


def _score_video_quality(ctx: QAContext) -> int:
    all_shots = [sh for sc in ctx.scenes for sh in sc.shots]
    if not all_shots:
        return 1

    total = len(all_shots)
    ready = sum(
        1 for sh in all_shots
        if any(a.get("status") == "ready" for a in sh.video_assets)
    )
    if ready == 0:
        return 1

    score = 2.0 + (ready / total) * 3.0
    return _clamp(score)


def _score_tts_quality(ctx: QAContext) -> int:
    all_shots = [sh for sc in ctx.scenes for sh in sc.shots]
    shots_with_narration = [sh for sh in all_shots if sh.narration_segment]
    if not shots_with_narration:
        return 3  # no narration needed

    with_voice = sum(
        1 for sh in shots_with_narration
        if any(v.get("status") == "ready" for v in sh.voice_tracks)
    )
    if with_voice == 0:
        return 1

    score = 2.0 + (with_voice / len(shots_with_narration)) * 3.0
    return _clamp(score)


def _score_subtitle_sync(ctx: QAContext) -> int:
    ready_subs = [s for s in ctx.subtitle_tracks if s.get("status") == "ready"]
    if not ready_subs:
        return 1

    score = 3.0
    latest = ready_subs[0]
    seg_count = latest.get("total_segments", 0)
    if seg_count > 0:
        score += 1.0

    sub_dur = latest.get("total_duration_ms", 0) or 0
    total_scene_dur_ms = sum((s.duration_estimate_sec or 0) * 1000 for s in ctx.scenes)
    if sub_dur > 0 and total_scene_dur_ms > 0:
        ratio = sub_dur / total_scene_dur_ms
        if 0.8 <= ratio <= 1.2:
            score += 1.0
        elif ratio < 0.5 or ratio > 1.5:
            score -= 1.0

    return _clamp(score)


def _score_final_output(ctx: QAContext) -> int:
    ready_tls = [t for t in ctx.timelines if t.get("status") == "composed"]
    if not ready_tls:
        return 1

    score = 3.0
    all_shots = [sh for sc in ctx.scenes for sh in sc.shots]
    total = max(len(all_shots), 1)

    video_coverage = sum(
        1 for sh in all_shots
        if any(a.get("status") == "ready" for a in sh.video_assets)
    ) / total
    score += video_coverage * 1.0

    if not ctx.failed_jobs:
        score += 0.5
    if not ctx.failed_provider_runs:
        score += 0.5

    return _clamp(score)


_SCORE_FUNCTIONS = {
    "script_quality": _score_script_quality,
    "scene_structure": _score_scene_structure,
    "shot_quality": _score_shot_quality,
    "frame_specificity": _score_frame_specificity,
    "style_consistency": _score_style_consistency,
    "image_quality": _score_image_quality,
    "video_quality": _score_video_quality,
    "tts_quality": _score_tts_quality,
    "subtitle_sync": _score_subtitle_sync,
    "final_output_quality": _score_final_output,
}


def run_auto_evaluation(ctx: QAContext) -> dict[str, int]:
    """Run all auto-evaluation criteria and return {key: score(1-5)}."""
    scores: dict[str, int] = {}
    for key in CRITERIA_KEYS:
        fn = _SCORE_FUNCTIONS.get(key)
        if fn:
            scores[key] = fn(ctx)
    return scores


def run_auto_evaluation_with_summary(ctx: QAContext) -> tuple[dict[str, int], float | None]:
    """Run auto evaluation and return (scores, weighted_average)."""
    scores = run_auto_evaluation(ctx)
    avg = compute_weighted_average(scores)
    return scores, avg
