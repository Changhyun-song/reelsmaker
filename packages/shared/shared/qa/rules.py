"""QA rule checks — pure functions operating on pre-fetched data.

Each check_* function receives a QAContext and returns a list of QAIssue.
New checks can be added by appending to RULE_REGISTRY at the bottom.
For future Claude-based critic, add checks with source="critic".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shared.schemas.qa import QAIssue


@dataclass
class ShotContext:
    shot_id: str
    scene_id: str
    order_index: int
    duration_sec: float | None
    status: str
    narration_segment: str | None
    asset_strategy: str | None
    frame_specs: list[dict] = field(default_factory=list)
    image_assets: list[dict] = field(default_factory=list)
    video_assets: list[dict] = field(default_factory=list)
    voice_tracks: list[dict] = field(default_factory=list)


@dataclass
class SceneContext:
    scene_id: str
    order_index: int
    duration_estimate_sec: float | None
    status: str
    narration_text: str | None
    shots: list[ShotContext] = field(default_factory=list)


@dataclass
class QAContext:
    project_id: str
    script_version_id: str | None
    target_duration_sec: float | None
    scenes: list[SceneContext] = field(default_factory=list)
    subtitle_tracks: list[dict] = field(default_factory=list)
    timelines: list[dict] = field(default_factory=list)
    failed_jobs: list[dict] = field(default_factory=list)
    failed_provider_runs: list[dict] = field(default_factory=list)


def check_shot_completeness(ctx: QAContext) -> list[QAIssue]:
    """Check each shot has frame specs, images, video, and voice."""
    issues: list[QAIssue] = []

    for scene in ctx.scenes:
        for shot in scene.shots:
            sid_short = shot.shot_id[:8]

            if not shot.frame_specs:
                issues.append(QAIssue(
                    scope="shot", target_type="shot", target_id=shot.shot_id,
                    check_type="missing_frame_specs",
                    severity="warning",
                    message=f"Shot #{shot.order_index+1} ({sid_short}): Frame spec이 없습니다",
                    suggestion="Shot 상세에서 'Frame 생성' 버튼을 눌러주세요",
                ))

            start_frames = [f for f in shot.frame_specs if f.get("frame_role") == "start"]
            end_frames = [f for f in shot.frame_specs if f.get("frame_role") == "end"]

            if shot.frame_specs and not start_frames:
                issues.append(QAIssue(
                    scope="shot", target_type="shot", target_id=shot.shot_id,
                    check_type="missing_start_frame",
                    severity="warning",
                    message=f"Shot #{shot.order_index+1} ({sid_short}): Start frame이 없습니다",
                    suggestion="Frame을 재생성하거나 start frame을 추가하세요",
                ))

            if shot.frame_specs and not end_frames:
                issues.append(QAIssue(
                    scope="shot", target_type="shot", target_id=shot.shot_id,
                    check_type="missing_end_frame",
                    severity="info",
                    message=f"Shot #{shot.order_index+1} ({sid_short}): End frame이 없습니다",
                    suggestion="End frame이 없으면 비디오 생성 시 일관성이 떨어질 수 있습니다",
                ))

            ready_images = [a for a in shot.image_assets if a.get("status") == "ready"]
            if not ready_images and shot.asset_strategy != "direct_video":
                issues.append(QAIssue(
                    scope="shot", target_type="shot", target_id=shot.shot_id,
                    check_type="missing_images",
                    severity="warning",
                    message=f"Shot #{shot.order_index+1} ({sid_short}): 생성된 이미지가 없습니다",
                    suggestion="Frame 상세에서 '이미지 생성' 버튼을 눌러주세요",
                ))

            ready_videos = [a for a in shot.video_assets if a.get("status") == "ready"]
            if not ready_videos:
                issues.append(QAIssue(
                    scope="shot", target_type="shot", target_id=shot.shot_id,
                    check_type="missing_video_clip",
                    severity="error",
                    message=f"Shot #{shot.order_index+1} ({sid_short}): 비디오 클립이 없습니다",
                    suggestion="Shot 상세에서 '비디오 생성' 버튼을 눌러주세요",
                ))

            ready_voice = [v for v in shot.voice_tracks if v.get("status") == "ready"]
            if not ready_voice and shot.narration_segment:
                issues.append(QAIssue(
                    scope="shot", target_type="shot", target_id=shot.shot_id,
                    check_type="no_voice_track",
                    severity="warning",
                    message=f"Shot #{shot.order_index+1} ({sid_short}): 나레이션이 있지만 TTS가 없습니다",
                    suggestion="Shot 상세에서 'TTS 생성' 버튼을 눌러주세요",
                ))

    return issues


def check_duration_mismatch(ctx: QAContext) -> list[QAIssue]:
    """Check duration consistency across scenes and shots."""
    issues: list[QAIssue] = []

    total_scene_dur = sum(s.duration_estimate_sec or 0 for s in ctx.scenes)
    if ctx.target_duration_sec and total_scene_dur > 0:
        ratio = total_scene_dur / ctx.target_duration_sec
        if ratio < 0.7 or ratio > 1.3:
            issues.append(QAIssue(
                scope="project", target_type="project", target_id=ctx.project_id,
                check_type="duration_conflict",
                severity="warning",
                message=f"Scene 총 길이({total_scene_dur:.0f}초)가 목표({ctx.target_duration_sec:.0f}초)와 {abs(1-ratio)*100:.0f}% 차이납니다",
                details={"total_scene_sec": total_scene_dur, "target_sec": ctx.target_duration_sec, "ratio": round(ratio, 2)},
                suggestion="Scene을 재생성하거나 목표 시간을 조정하세요",
            ))

    for scene in ctx.scenes:
        if not scene.shots:
            continue
        total_shot_dur = sum(sh.duration_sec or 0 for sh in scene.shots)
        scene_dur = scene.duration_estimate_sec or 0
        if scene_dur > 0 and total_shot_dur > 0:
            ratio = total_shot_dur / scene_dur
            if ratio < 0.7 or ratio > 1.3:
                issues.append(QAIssue(
                    scope="scene", target_type="scene", target_id=scene.scene_id,
                    check_type="duration_conflict",
                    severity="warning",
                    message=f"Scene #{scene.order_index+1}: Shot 합계({total_shot_dur:.1f}초)가 Scene 길이({scene_dur:.1f}초)와 불일치",
                    details={"shot_total_sec": total_shot_dur, "scene_sec": scene_dur},
                    suggestion="Shot을 재생성하거나 Scene 길이를 조정하세요",
                ))

        for shot in scene.shots:
            if shot.duration_sec and (shot.duration_sec < 1.0 or shot.duration_sec > 15.0):
                issues.append(QAIssue(
                    scope="shot", target_type="shot", target_id=shot.shot_id,
                    check_type="duration_conflict",
                    severity="info",
                    message=f"Shot #{shot.order_index+1} ({shot.shot_id[:8]}): 길이가 {shot.duration_sec:.1f}초로 비정상적입니다",
                    suggestion="2~8초 범위가 일반적입니다. Shot을 재생성하세요",
                ))

    return issues


def check_subtitle_mismatch(ctx: QAContext) -> list[QAIssue]:
    """Check subtitle track existence and consistency."""
    issues: list[QAIssue] = []

    ready_subs = [s for s in ctx.subtitle_tracks if s.get("status") == "ready"]
    if not ready_subs:
        issues.append(QAIssue(
            scope="project", target_type="project", target_id=ctx.project_id,
            check_type="subtitle_missing",
            severity="warning",
            message="자막 트랙이 생성되지 않았습니다",
            suggestion="자막 생성 패널에서 '자막 생성'을 실행하세요",
        ))
    else:
        latest_sub = ready_subs[0]
        total_shots = sum(len(sc.shots) for sc in ctx.scenes)
        seg_count = latest_sub.get("total_segments", 0)
        if seg_count == 0:
            issues.append(QAIssue(
                scope="project", target_type="project", target_id=ctx.project_id,
                check_type="subtitle_missing",
                severity="warning",
                message="자막 트랙은 있지만 세그먼트가 비어 있습니다",
                suggestion="자막을 재생성하세요",
            ))

        sub_dur = latest_sub.get("total_duration_ms", 0) or 0
        total_scene_dur_ms = sum((s.duration_estimate_sec or 0) * 1000 for s in ctx.scenes)
        if sub_dur > 0 and total_scene_dur_ms > 0:
            ratio = sub_dur / total_scene_dur_ms
            if ratio < 0.5 or ratio > 1.5:
                issues.append(QAIssue(
                    scope="project", target_type="project", target_id=ctx.project_id,
                    check_type="subtitle_duration_mismatch",
                    severity="warning",
                    message=f"자막 길이({sub_dur/1000:.1f}초)와 영상 길이({total_scene_dur_ms/1000:.1f}초)가 크게 다릅니다",
                    suggestion="TTS를 재생성한 후 자막을 다시 생성하세요",
                ))

    return issues


def check_render_readiness(ctx: QAContext) -> list[QAIssue]:
    """Check if project is ready for final render."""
    issues: list[QAIssue] = []

    if not ctx.scenes:
        issues.append(QAIssue(
            scope="project", target_type="project", target_id=ctx.project_id,
            check_type="no_scenes",
            severity="error",
            message="Scene이 생성되지 않았습니다",
            suggestion="대본을 먼저 생성한 후 Scene 분해를 실행하세요",
        ))
        return issues

    total_shots = sum(len(sc.shots) for sc in ctx.scenes)
    if total_shots == 0:
        issues.append(QAIssue(
            scope="project", target_type="project", target_id=ctx.project_id,
            check_type="no_shots",
            severity="error",
            message="Shot이 하나도 없습니다",
            suggestion="각 Scene에서 Shot 분해를 실행하세요",
        ))
        return issues

    shots_with_video = 0
    shots_with_audio = 0
    for scene in ctx.scenes:
        for shot in scene.shots:
            if any(a.get("status") == "ready" for a in shot.video_assets):
                shots_with_video += 1
            if any(v.get("status") == "ready" for v in shot.voice_tracks):
                shots_with_audio += 1

    if shots_with_video < total_shots:
        missing = total_shots - shots_with_video
        issues.append(QAIssue(
            scope="project", target_type="project", target_id=ctx.project_id,
            check_type="render_not_ready",
            severity="error" if shots_with_video == 0 else "warning",
            message=f"렌더 준비 미완: {missing}/{total_shots}개 Shot에 비디오 없음",
            details={"total": total_shots, "with_video": shots_with_video, "missing": missing},
            suggestion="비디오가 없는 Shot에서 '비디오 생성'을 실행하세요",
        ))

    ready_tls = [t for t in ctx.timelines if t.get("status") == "composed"]
    if not ready_tls:
        issues.append(QAIssue(
            scope="project", target_type="project", target_id=ctx.project_id,
            check_type="no_timeline",
            severity="error",
            message="타임라인이 조립되지 않았습니다",
            suggestion="'타임라인 조립'을 실행하세요",
        ))

    return issues


def check_provider_failures(ctx: QAContext) -> list[QAIssue]:
    """Summarize recent provider/job failures."""
    issues: list[QAIssue] = []

    if ctx.failed_jobs:
        by_type: dict[str, int] = {}
        for j in ctx.failed_jobs:
            jt = j.get("job_type", "unknown")
            by_type[jt] = by_type.get(jt, 0) + 1

        summary_parts = [f"{t}: {c}건" for t, c in by_type.items()]
        issues.append(QAIssue(
            scope="project", target_type="project", target_id=ctx.project_id,
            check_type="failed_jobs",
            severity="warning",
            message=f"실패한 작업 {len(ctx.failed_jobs)}건 — {', '.join(summary_parts)}",
            details={"by_type": by_type, "total": len(ctx.failed_jobs)},
            suggestion="실패한 작업을 재시도하거나 해당 단계를 재생성하세요",
        ))

    if ctx.failed_provider_runs:
        providers: dict[str, int] = {}
        for pr in ctx.failed_provider_runs:
            pn = pr.get("provider_name", "unknown")
            providers[pn] = providers.get(pn, 0) + 1

        parts = [f"{p}: {c}건" for p, c in providers.items()]
        issues.append(QAIssue(
            scope="project", target_type="project", target_id=ctx.project_id,
            check_type="provider_failures",
            severity="warning",
            message=f"AI 프로바이더 실패 {len(ctx.failed_provider_runs)}건 — {', '.join(parts)}",
            details={"by_provider": providers},
            suggestion="API 키와 프로바이더 상태를 확인하세요",
        ))

    return issues


def check_scene_completeness(ctx: QAContext) -> list[QAIssue]:
    """Check each scene has shots and basic data."""
    issues: list[QAIssue] = []

    for scene in ctx.scenes:
        if not scene.shots:
            issues.append(QAIssue(
                scope="scene", target_type="scene", target_id=scene.scene_id,
                check_type="no_shots",
                severity="warning",
                message=f"Scene #{scene.order_index+1} ({scene.scene_id[:8]}): Shot이 없습니다",
                suggestion="Scene에서 'Shot 분해'를 실행하세요",
            ))
        if not scene.narration_text:
            issues.append(QAIssue(
                scope="scene", target_type="scene", target_id=scene.scene_id,
                check_type="missing_narration",
                severity="info",
                message=f"Scene #{scene.order_index+1} ({scene.scene_id[:8]}): 나레이션 텍스트가 비어 있습니다",
                suggestion="Scene을 재생성하세요",
            ))

    return issues


def check_shot_transition_coherence(ctx: QAContext) -> list[QAIssue]:
    """Check consecutive shots for transition and pacing anomalies.

    Flags:
    - Consecutive static shots (no camera movement) — feels stagnant
    - Same shot_type repeated 3+ times — monotonous rhythm
    - Duration jump > 3x between adjacent shots — pacing whiplash
    - Missing narration gap (no audio) between narrated shots — breathless
    - Same environment repeated without camera change — visual redundancy
    """
    issues: list[QAIssue] = []

    all_shots: list[ShotContext] = []
    for scene in ctx.scenes:
        all_shots.extend(scene.shots)

    if len(all_shots) < 2:
        return issues

    consecutive_static = 0
    type_streak = 1
    prev_type = None

    for i in range(len(all_shots)):
        shot = all_shots[i]
        sid_short = shot.shot_id[:8]

        # Static detection
        cam = (shot.frame_specs[0].get("camera_angle", "") if shot.frame_specs else "").lower()
        movement_hints = ["zoom", "pan", "tilt", "dolly", "track", "push", "pull", "crane"]
        has_movement = any(h in cam for h in movement_hints)
        if not has_movement:
            consecutive_static += 1
        else:
            consecutive_static = 0

        if consecutive_static >= 3:
            issues.append(QAIssue(
                scope="shot", target_type="shot", target_id=shot.shot_id,
                check_type="transition_stagnant",
                severity="info",
                message=f"Shot #{shot.order_index+1} ({sid_short}): 연속 {consecutive_static}개 정적 shot — 리듬이 단조로울 수 있음",
                suggestion="중간에 카메라 움직임(zoom, pan)이 있는 shot을 추가하거나 재생성하세요",
            ))

        # Shot type streak
        if shot.asset_strategy == prev_type and prev_type is not None:
            type_streak += 1
        else:
            type_streak = 1
        prev_type = shot.asset_strategy

        if type_streak >= 3:
            issues.append(QAIssue(
                scope="shot", target_type="shot", target_id=shot.shot_id,
                check_type="transition_monotonous",
                severity="info",
                message=f"Shot #{shot.order_index+1} ({sid_short}): 동일 유형({shot.asset_strategy}) {type_streak}연속 — 시각적 다양성 부족",
                suggestion="shot_type이나 camera_framing을 다양화하세요",
            ))

        # Duration jump
        if i > 0:
            prev = all_shots[i - 1]
            dur = shot.duration_sec or 4.0
            prev_dur = prev.duration_sec or 4.0
            if dur > 0 and prev_dur > 0:
                ratio = max(dur, prev_dur) / max(min(dur, prev_dur), 0.1)
                if ratio > 3.0:
                    issues.append(QAIssue(
                        scope="shot", target_type="shot", target_id=shot.shot_id,
                        check_type="transition_pacing_jump",
                        severity="warning",
                        message=f"Shot #{shot.order_index+1} ({sid_short}): 이전 shot({prev_dur:.1f}s)과 길이 차이 {ratio:.1f}배 — 페이싱 불균형",
                        details={"this_dur": dur, "prev_dur": prev_dur, "ratio": round(ratio, 1)},
                        suggestion="Shot 길이를 조정하거나 중간에 전환 shot을 추가하세요",
                    ))

            # Narration gap check
            prev_has_narr = bool(prev.narration_segment and prev.narration_segment.strip())
            this_has_narr = bool(shot.narration_segment and shot.narration_segment.strip())
            prev_has_voice = any(v.get("status") == "ready" for v in prev.voice_tracks)
            this_has_voice = any(v.get("status") == "ready" for v in shot.voice_tracks)

            if prev_has_narr and this_has_narr and prev_has_voice and not this_has_voice:
                issues.append(QAIssue(
                    scope="shot", target_type="shot", target_id=shot.shot_id,
                    check_type="transition_missing_audio",
                    severity="warning",
                    message=f"Shot #{shot.order_index+1} ({sid_short}): 나레이션이 있지만 TTS 없음 — 이전 shot에는 있어 청각적 단절",
                    suggestion="이 shot에도 TTS를 생성하세요",
                ))

    return issues


RULE_REGISTRY: list[tuple[str, Any]] = [
    ("shot_completeness", check_shot_completeness),
    ("scene_completeness", check_scene_completeness),
    ("duration_mismatch", check_duration_mismatch),
    ("subtitle_mismatch", check_subtitle_mismatch),
    ("render_readiness", check_render_readiness),
    ("provider_failures", check_provider_failures),
    ("shot_transition_coherence", check_shot_transition_coherence),
]
