"""Timeline composer — assembles shots, assets, voice tracks, subtitles
into a render-ready TimelineData structure.

v2: Integrates editing rules for format-specific pacing, transitions,
    image motion presets, pause/beat insertion, and hook handling.

Pure function: takes pre-fetched data, returns TimelineData.
No ORM or DB access inside this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from shared.editing.motion import resolve_image_motion
from shared.editing.pacing import (
    FormatProfile,
    classify_shot_zone,
    get_format_profile,
    get_pacing_rules,
)
from shared.editing.transitions import resolve_transition
from shared.schemas.timeline import (
    AudioSegment,
    ImageMotionSpec,
    PauseSegment,
    TimelineData,
    TransitionSpec,
    VideoSegment,
)


@dataclass
class ShotInput:
    """Pre-fetched shot data for composition."""
    shot_id: str
    scene_id: str
    order_index: int
    scene_order_index: int
    duration_sec: float | None
    shot_type: str | None = None
    camera_movement: str | None = None
    asset_strategy: str | None = None
    transition_in: str | None = None
    transition_out: str | None = None
    narration_segment: str | None = None

    video_asset_id: str | None = None
    video_storage_key: str | None = None
    video_duration_ms: int | None = None

    image_asset_id: str | None = None
    image_storage_key: str | None = None

    voice_track_id: str | None = None
    voice_asset_id: str | None = None
    voice_storage_key: str | None = None
    voice_duration_ms: int | None = None
    voice_id: str | None = None


@dataclass
class ComposerConfig:
    default_shot_duration_ms: int = 4000
    default_transition_ms: int = 0
    default_image_motion: str = "ken_burns"
    output_width: int = 1080
    output_height: int = 1920
    output_fps: int = 30
    format_name: str = "shorts"


def _estimate_total_duration(shots: list[ShotInput], default_ms: int) -> int:
    total = 0
    for s in shots:
        if s.video_asset_id and s.video_duration_ms:
            total += s.video_duration_ms
        elif s.duration_sec:
            total += int(s.duration_sec * 1000)
        else:
            total += default_ms
    return total


def compose_timeline(
    shots: list[ShotInput],
    subtitle_track_id: str | None = None,
    bgm_asset_id: str | None = None,
    config: ComposerConfig | None = None,
) -> TimelineData:
    """Compose shots into a render-ready timeline with editing rules.

    Applies:
    - Format-specific pacing (hook/body/climax/outro zones)
    - Transition presets based on shot hints and scene boundaries
    - Ken Burns motion presets based on camera movement and zone
    - Pause/beat insertion at scene boundaries and after hooks
    - Intro fade-in and outro fade-out
    """
    cfg = config or ComposerConfig()
    profile = get_format_profile(cfg.format_name)
    warnings: list[str] = []

    sorted_shots = sorted(shots, key=lambda s: (s.scene_order_index, s.order_index))

    estimated_total_ms = _estimate_total_duration(sorted_shots, cfg.default_shot_duration_ms)

    video_segments: list[VideoSegment] = []
    audio_segments: list[AudioSegment] = []
    pause_segments: list[PauseSegment] = []
    cursor_ms = 0

    prev_scene_id: str | None = None
    total_shots = len(sorted_shots)

    for idx, shot in enumerate(sorted_shots):
        is_first = idx == 0
        is_last = idx == total_shots - 1
        scene_boundary = prev_scene_id is not None and shot.scene_id != prev_scene_id

        # ── Zone classification ──
        zone = classify_shot_zone(
            shot_index=idx,
            total_shots=total_shots,
            elapsed_ms=cursor_ms,
            total_duration_ms=estimated_total_ms,
            profile=profile,
        )
        pacing = get_pacing_rules(profile, zone)

        # ── Scene gap pause ──
        if scene_boundary:
            gap_ms = max(profile.scene_gap_ms, pacing.pause_after_scene_ms)
            if gap_ms > 0:
                pause_segments.append(PauseSegment(
                    index=len(pause_segments),
                    start_ms=cursor_ms,
                    end_ms=cursor_ms + gap_ms,
                    duration_ms=gap_ms,
                    pause_type="scene_gap",
                    visual="fade_black" if profile.scene_transition == "dip_to_black" else "hold_last",
                    after_shot_id=sorted_shots[idx - 1].shot_id if idx > 0 else None,
                ))
                cursor_ms += gap_ms

        # ── Hook pause (after hook zone ends) ──
        if idx > 0 and zone != "hook":
            prev_zone = classify_shot_zone(
                shot_index=idx - 1,
                total_shots=total_shots,
                elapsed_ms=cursor_ms - (sorted_shots[idx - 1].video_duration_ms or int((sorted_shots[idx - 1].duration_sec or 4.0) * 1000)),
                total_duration_ms=estimated_total_ms,
                profile=profile,
            )
            if prev_zone == "hook" and pacing.pause_after_hook_ms > 0:
                hook_pause = pacing.pause_after_hook_ms
                pause_segments.append(PauseSegment(
                    index=len(pause_segments),
                    start_ms=cursor_ms,
                    end_ms=cursor_ms + hook_pause,
                    duration_ms=hook_pause,
                    pause_type="hook_pause",
                    visual="hold_last",
                    after_shot_id=sorted_shots[idx - 1].shot_id,
                ))
                cursor_ms += hook_pause

        # ── Visual duration ──
        if shot.video_asset_id and shot.video_duration_ms:
            visual_dur_ms = shot.video_duration_ms
        elif shot.duration_sec:
            visual_dur_ms = int(shot.duration_sec * 1000)
        else:
            visual_dur_ms = cfg.default_shot_duration_ms

        # Clamp to pacing limits
        visual_dur_ms = max(pacing.min_shot_duration_ms, min(pacing.max_shot_duration_ms, visual_dur_ms))

        # ── Asset type + motion ──
        if shot.video_asset_id:
            asset_type = "video"
            asset_id = shot.video_asset_id
            storage_key = shot.video_storage_key
            image_motion = None
        elif shot.image_asset_id:
            asset_type = "image"
            asset_id = shot.image_asset_id
            storage_key = shot.image_storage_key
            mp = resolve_image_motion(
                camera_movement=shot.camera_movement,
                shot_type=shot.shot_type,
                zone=zone,
                shot_index=idx,
            )
            image_motion = ImageMotionSpec(
                effect=mp.effect,
                zoom_start=mp.zoom_start,
                zoom_end=mp.zoom_end,
                pan_direction=mp.pan_direction,
                easing=mp.easing,
                preset_name=mp.name,
            )
            warnings.append(f"Shot #{idx+1} ({shot.shot_id[:8]}): image-only → {mp.name}")
        else:
            asset_type = "missing"
            asset_id = None
            storage_key = None
            image_motion = None
            warnings.append(f"Shot #{idx+1} ({shot.shot_id[:8]}): no visual asset")

        # ── Transitions ──
        t_in_preset = resolve_transition(
            hint=shot.transition_in,
            scene_boundary=scene_boundary,
            is_first=is_first,
            format_default=profile.default_transition,
            scene_default=profile.scene_transition,
        )
        t_out_preset = resolve_transition(
            hint=shot.transition_out,
            is_last=is_last,
            format_default=profile.default_transition,
            scene_default=profile.scene_transition,
        )

        transition_in = TransitionSpec(
            type=t_in_preset.type,
            duration_ms=t_in_preset.duration_ms if not is_first else profile.intro_fade_in_ms or t_in_preset.duration_ms,
            params=dict(t_in_preset.params),
            ffmpeg_xfade_name=t_in_preset.ffmpeg_xfade_name,
        )
        transition_out = TransitionSpec(
            type=t_out_preset.type,
            duration_ms=t_out_preset.duration_ms if not is_last else profile.outro_fade_out_ms or t_out_preset.duration_ms,
            params=dict(t_out_preset.params),
            ffmpeg_xfade_name=t_out_preset.ffmpeg_xfade_name,
        )

        # ── Beat marker (micro-pause for rhythm) ──
        beat_ms = pacing.beat_marker_ms
        if beat_ms > 0 and not is_last and not scene_boundary:
            if idx > 0 and idx % 2 == 0:
                pause_segments.append(PauseSegment(
                    index=len(pause_segments),
                    start_ms=cursor_ms + visual_dur_ms,
                    end_ms=cursor_ms + visual_dur_ms + beat_ms,
                    duration_ms=beat_ms,
                    pause_type="beat",
                    visual="hold_last",
                    after_shot_id=shot.shot_id,
                ))

        vs = VideoSegment(
            index=idx,
            shot_id=shot.shot_id,
            scene_id=shot.scene_id,
            start_ms=cursor_ms,
            end_ms=cursor_ms + visual_dur_ms,
            duration_ms=visual_dur_ms,
            asset_type=asset_type,
            asset_id=asset_id,
            storage_key=storage_key,
            transition_in=transition_in,
            transition_out=transition_out,
            image_motion=image_motion,
            pacing_zone=zone,
            shot_metadata={
                "shot_type": shot.shot_type,
                "camera_movement": shot.camera_movement,
                "asset_strategy": shot.asset_strategy,
            },
        )
        video_segments.append(vs)

        # ── Audio segment ──
        audio_dur_ms = shot.voice_duration_ms or visual_dur_ms
        audio_status = "ready" if shot.voice_asset_id else "missing"
        if not shot.voice_asset_id and shot.narration_segment:
            warnings.append(f"Shot #{idx+1} ({shot.shot_id[:8]}): narration exists but no TTS audio")

        audio_seg = AudioSegment(
            index=idx,
            shot_id=shot.shot_id,
            start_ms=cursor_ms,
            end_ms=cursor_ms + audio_dur_ms,
            duration_ms=audio_dur_ms,
            asset_id=shot.voice_asset_id,
            storage_key=shot.voice_storage_key,
            voice_track_id=shot.voice_track_id,
            voice_id=shot.voice_id,
            status=audio_status,
        )
        audio_segments.append(audio_seg)

        cursor_ms += visual_dur_ms

        # Add beat after shot if applicable
        if beat_ms > 0 and not is_last and not scene_boundary and idx > 0 and idx % 2 == 0:
            cursor_ms += beat_ms

        prev_scene_id = shot.scene_id

    total_duration_ms = cursor_ms

    if not subtitle_track_id:
        warnings.append("No subtitle track linked")

    return TimelineData(
        version=2,
        format_profile=cfg.format_name,
        total_duration_ms=total_duration_ms,
        video_segments=video_segments,
        audio_segments=audio_segments,
        pause_segments=pause_segments,
        subtitle_track_id=subtitle_track_id,
        bgm_asset_id=bgm_asset_id,
        intro_fade_in_ms=profile.intro_fade_in_ms,
        outro_fade_out_ms=profile.outro_fade_out_ms,
        warnings=warnings,
        output_settings={
            "width": cfg.output_width,
            "height": cfg.output_height,
            "fps": cfg.output_fps,
            "format": "mp4",
            "codec": "h264",
        },
    )
