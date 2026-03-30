"""Export / Import API — project JSON, SRT, MP4, asset manifest."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.asset import Asset
from shared.models.character_profile import CharacterProfile
from shared.models.frame_spec import FrameSpec
from shared.models.project import Project
from shared.models.render_job import RenderJob
from shared.models.scene import Scene
from shared.models.script_version import ScriptVersion
from shared.models.shot import Shot
from shared.models.style_preset import StylePreset
from shared.models.subtitle_track import SubtitleTrack
from shared.models.timeline import Timeline
from shared.models.voice_track import VoiceTrack
from shared.storage import get_presigned_url, upload_bytes, generate_storage_key

router = APIRouter()

EXPORT_FORMAT_VERSION = "1.0"


# ── Helpers ───────────────────────────────────────────


def _ser(val) -> str | None:
    """Serialize UUID / datetime to string, pass None through."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def _asset_dict(a: Asset) -> dict:
    return {
        "id": _ser(a.id),
        "parent_type": a.parent_type,
        "parent_id": _ser(a.parent_id),
        "asset_type": a.asset_type,
        "storage_key": a.storage_key,
        "filename": a.filename,
        "mime_type": a.mime_type,
        "file_size_bytes": a.file_size_bytes,
        "metadata": a.metadata_,
        "version": a.version,
        "status": a.status,
        "is_selected": a.is_selected,
        "created_at": _ser(a.created_at),
    }


async def _build_project_json(
    db: AsyncSession,
    project_id: UUID,
) -> dict:
    """Build a comprehensive project export dictionary."""

    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    # Style presets
    sp_result = await db.execute(
        select(StylePreset).where(StylePreset.project_id == project_id)
    )
    style_presets = [
        {
            "id": _ser(s.id), "name": s.name, "description": s.description,
            "style_keywords": s.style_keywords, "color_palette": s.color_palette,
            "rendering_style": s.rendering_style, "camera_language": s.camera_language,
            "lighting_rules": s.lighting_rules, "negative_rules": s.negative_rules,
            "prompt_prefix": s.prompt_prefix, "prompt_suffix": s.prompt_suffix,
            "negative_prompt": s.negative_prompt,
        }
        for s in sp_result.scalars().all()
    ]

    # Characters
    cp_result = await db.execute(
        select(CharacterProfile).where(CharacterProfile.project_id == project_id)
    )
    characters = [
        {
            "id": _ser(c.id), "name": c.name, "role": c.role,
            "appearance": c.appearance, "outfit": c.outfit,
            "age_impression": c.age_impression, "personality": c.personality,
            "facial_traits": c.facial_traits, "pose_rules": c.pose_rules,
            "forbidden_changes": c.forbidden_changes,
            "visual_prompt": c.visual_prompt, "voice_id": c.voice_id,
        }
        for c in cp_result.scalars().all()
    ]

    # Script versions
    sv_result = await db.execute(
        select(ScriptVersion)
        .where(ScriptVersion.project_id == project_id)
        .order_by(ScriptVersion.version.desc())
    )
    script_versions_raw = list(sv_result.scalars().all())

    script_versions = []
    for sv in script_versions_raw:
        # Scenes for this version
        scenes_result = await db.execute(
            select(Scene).where(Scene.script_version_id == sv.id).order_by(Scene.order_index)
        )
        scenes_list = []
        for scene in scenes_result.scalars().all():
            # Shots for this scene
            shots_result = await db.execute(
                select(Shot).where(Shot.scene_id == scene.id).order_by(Shot.order_index)
            )
            shots_list = []
            for shot in shots_result.scalars().all():
                # Frames for this shot
                fs_result = await db.execute(
                    select(FrameSpec).where(FrameSpec.shot_id == shot.id).order_by(FrameSpec.order_index)
                )
                frames_list = [
                    {
                        "id": _ser(f.id), "order_index": f.order_index,
                        "frame_role": f.frame_role, "composition": f.composition,
                        "subject_position": f.subject_position, "camera_angle": f.camera_angle,
                        "lens_feel": f.lens_feel, "lighting": f.lighting,
                        "mood": f.mood, "action_pose": f.action_pose,
                        "background_description": f.background_description,
                        "continuity_notes": f.continuity_notes,
                        "forbidden_elements": f.forbidden_elements,
                        "visual_prompt": f.visual_prompt, "negative_prompt": f.negative_prompt,
                        "status": f.status,
                    }
                    for f in fs_result.scalars().all()
                ]

                # Voice tracks for this shot
                vt_result = await db.execute(
                    select(VoiceTrack).where(VoiceTrack.shot_id == shot.id).order_by(VoiceTrack.created_at.desc())
                )
                voice_tracks = [
                    {
                        "id": _ser(v.id), "voice_id": v.voice_id,
                        "speaker_name": v.speaker_name, "language": v.language,
                        "speed": v.speed, "emotion": v.emotion,
                        "duration_ms": v.duration_ms, "status": v.status,
                        "is_selected": v.is_selected,
                    }
                    for v in vt_result.scalars().all()
                ]

                shots_list.append({
                    "id": _ser(shot.id), "order_index": shot.order_index,
                    "shot_type": shot.shot_type, "description": shot.description,
                    "camera_movement": shot.camera_movement,
                    "camera_framing": shot.camera_framing,
                    "duration_sec": shot.duration_sec, "status": shot.status,
                    "purpose": shot.purpose, "subject": shot.subject,
                    "environment": shot.environment, "emotion": shot.emotion,
                    "narration_segment": shot.narration_segment,
                    "transition_in": shot.transition_in,
                    "transition_out": shot.transition_out,
                    "asset_strategy": shot.asset_strategy,
                    "frames": frames_list,
                    "voice_tracks": voice_tracks,
                })

            scenes_list.append({
                "id": _ser(scene.id), "order_index": scene.order_index,
                "title": scene.title, "description": scene.description,
                "setting": scene.setting, "mood": scene.mood,
                "duration_estimate_sec": scene.duration_estimate_sec,
                "status": scene.status, "purpose": scene.purpose,
                "narration_text": scene.narration_text,
                "emotional_tone": scene.emotional_tone,
                "visual_intent": scene.visual_intent,
                "transition_hint": scene.transition_hint,
                "shots": shots_list,
            })

        script_versions.append({
            "id": _ser(sv.id), "version": sv.version,
            "status": sv.status, "raw_text": sv.raw_text,
            "input_params": sv.input_params, "plan_json": sv.plan_json,
            "created_at": _ser(sv.created_at),
            "scenes": scenes_list,
        })

    # Subtitle tracks
    sub_result = await db.execute(
        select(SubtitleTrack)
        .where(SubtitleTrack.project_id == project_id)
        .order_by(SubtitleTrack.created_at.desc())
    )
    subtitle_tracks = [
        {
            "id": _ser(s.id), "script_version_id": _ser(s.script_version_id),
            "language": s.language, "format": s.format,
            "timing_source": s.timing_source,
            "total_segments": s.total_segments,
            "total_duration_ms": s.total_duration_ms,
            "status": s.status,
        }
        for s in sub_result.scalars().all()
    ]

    # Timelines
    tl_result = await db.execute(
        select(Timeline).where(Timeline.project_id == project_id).order_by(Timeline.created_at.desc())
    )
    timelines = [
        {
            "id": _ser(t.id), "script_version_id": _ser(t.script_version_id),
            "total_duration_ms": t.total_duration_ms,
            "status": t.status, "segments": t.segments,
            "created_at": _ser(t.created_at),
        }
        for t in tl_result.scalars().all()
    ]

    # Render jobs
    rj_result = await db.execute(
        select(RenderJob).where(RenderJob.project_id == project_id).order_by(RenderJob.created_at.desc())
    )
    render_jobs = [
        {
            "id": _ser(rj.id), "timeline_id": _ser(rj.timeline_id),
            "status": rj.status, "progress": rj.progress,
            "output_asset_id": _ser(rj.output_asset_id),
            "output_settings": rj.output_settings,
            "created_at": _ser(rj.created_at),
            "completed_at": _ser(rj.completed_at),
        }
        for rj in rj_result.scalars().all()
    ]

    # Assets summary (no binary data, just metadata)
    assets_result = await db.execute(
        select(Asset).where(Asset.project_id == project_id).order_by(Asset.created_at.desc())
    )
    assets = [_asset_dict(a) for a in assets_result.scalars().all()]

    return {
        "_export_meta": {
            "format_version": EXPORT_FORMAT_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "app": "reelsmaker",
        },
        "project": {
            "id": _ser(project.id),
            "title": project.title,
            "description": project.description,
            "status": project.status,
            "settings": project.settings,
            "active_style_preset_id": _ser(project.active_style_preset_id),
            "created_at": _ser(project.created_at),
            "updated_at": _ser(project.updated_at),
        },
        "style_presets": style_presets,
        "characters": characters,
        "script_versions": script_versions,
        "subtitle_tracks": subtitle_tracks,
        "timelines": timelines,
        "render_jobs": render_jobs,
        "assets": assets,
    }


# ── Export Endpoints ──────────────────────────────────


@router.get("/{project_id}/export/json")
async def export_project_json(
    project_id: UUID,
    save_as_asset: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Export complete project data as JSON.

    If save_as_asset=true, also uploads to S3 and creates an Asset record.
    """
    data = await _build_project_json(db, project_id)

    if save_as_asset:
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        key = generate_storage_key(
            str(project_id), "project", str(project_id),
            extension="json",
        )
        upload_bytes(key, json_bytes, content_type="application/json")

        asset = Asset(
            project_id=project_id,
            parent_type="project",
            parent_id=project_id,
            asset_type="project_export",
            storage_key=key,
            filename=f"{data['project']['title']}_export.json",
            mime_type="application/json",
            file_size_bytes=len(json_bytes),
            metadata_={"format_version": EXPORT_FORMAT_VERSION},
            status="ready",
        )
        db.add(asset)
        await db.flush()
        await db.refresh(asset)
        data["_export_meta"]["asset_id"] = str(asset.id)

    return JSONResponse(content=data)


@router.get("/{project_id}/export/srt")
async def export_srt(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Download the latest ready SRT subtitle as plain text."""
    track = (
        await db.execute(
            select(SubtitleTrack)
            .where(
                SubtitleTrack.project_id == project_id,
                SubtitleTrack.status == "ready",
            )
            .order_by(SubtitleTrack.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not track or not track.content:
        raise HTTPException(404, "No ready SRT content available")

    return PlainTextResponse(
        content=track.content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="subtitles.{track.format}"',
        },
    )


@router.get("/{project_id}/export/mp4")
async def export_mp4(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get presigned URL for the latest completed render MP4."""
    rj = (
        await db.execute(
            select(RenderJob)
            .where(
                RenderJob.project_id == project_id,
                RenderJob.status == "completed",
            )
            .order_by(RenderJob.completed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not rj or not rj.output_asset_id:
        raise HTTPException(404, "No completed render found")

    asset = (
        await db.execute(select(Asset).where(Asset.id == rj.output_asset_id))
    ).scalar_one_or_none()
    if not asset or not asset.storage_key:
        raise HTTPException(404, "Render output asset not found")

    url = get_presigned_url(asset.storage_key, expires_in=7200)
    return {
        "url": url,
        "filename": asset.filename or "render_output.mp4",
        "file_size_bytes": asset.file_size_bytes,
        "metadata": asset.metadata_,
    }


@router.get("/{project_id}/export/manifest")
async def export_asset_manifest(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Export a manifest of all project assets with download URLs."""
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    assets_result = await db.execute(
        select(Asset)
        .where(Asset.project_id == project_id, Asset.status == "ready")
        .order_by(Asset.created_at.desc())
    )
    assets = list(assets_result.scalars().all())

    manifest_items = []
    by_type: dict[str, int] = {}
    total_size = 0

    for a in assets:
        url = None
        if a.storage_key:
            try:
                url = get_presigned_url(a.storage_key, expires_in=7200)
            except Exception:
                pass

        by_type[a.asset_type] = by_type.get(a.asset_type, 0) + 1
        total_size += a.file_size_bytes or 0

        manifest_items.append({
            "id": str(a.id),
            "parent_type": a.parent_type,
            "parent_id": str(a.parent_id),
            "asset_type": a.asset_type,
            "storage_key": a.storage_key,
            "filename": a.filename,
            "mime_type": a.mime_type,
            "file_size_bytes": a.file_size_bytes,
            "is_selected": a.is_selected,
            "url": url,
            "created_at": str(a.created_at),
        })

    return {
        "project_id": str(project_id),
        "project_title": project.title,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_assets": len(assets),
            "total_size_bytes": total_size,
            "by_type": by_type,
        },
        "assets": manifest_items,
    }


# ── Import Endpoint (Foundation) ─────────────────────


class ImportRequest(BaseModel):
    """Import request schema — foundation for future full import."""
    project_json: dict = Field(..., description="Full project JSON from export")
    mode: str = Field(
        default="preview",
        pattern=r"^(preview|create)$",
        description="preview = validate only, create = actually import",
    )


class ImportPreviewResponse(BaseModel):
    valid: bool
    format_version: str | None
    project_title: str | None
    script_versions_count: int
    scenes_count: int
    shots_count: int
    assets_count: int
    warnings: list[str]


@router.post(
    "/{project_id}/import",
    response_model=ImportPreviewResponse,
)
async def import_project(
    project_id: UUID,
    body: ImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Import project data (preview mode only for now).

    Currently validates the import JSON structure and returns a summary.
    Full import (mode='create') is planned for a future version.
    """
    data = body.project_json
    warnings: list[str] = []

    meta = data.get("_export_meta", {})
    fmt_ver = meta.get("format_version")
    if not fmt_ver:
        warnings.append("Missing format_version — export may be from an older version")

    proj = data.get("project", {})
    title = proj.get("title")
    if not title:
        warnings.append("Project title is missing")

    svs = data.get("script_versions", [])
    scenes_count = 0
    shots_count = 0
    for sv in svs:
        scenes = sv.get("scenes", [])
        scenes_count += len(scenes)
        for sc in scenes:
            shots_count += len(sc.get("shots", []))

    assets = data.get("assets", [])

    valid = len(warnings) == 0 or all("Missing" not in w for w in warnings)

    if body.mode == "create":
        warnings.append("Full import is not yet implemented — only preview is available")
        valid = False

    return ImportPreviewResponse(
        valid=valid,
        format_version=fmt_ver,
        project_title=title,
        script_versions_count=len(svs),
        scenes_count=scenes_count,
        shots_count=shots_count,
        assets_count=len(assets),
        warnings=warnings,
    )
