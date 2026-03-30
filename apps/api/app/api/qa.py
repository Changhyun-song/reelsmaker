"""QA / Critic API — run checks, list results, resolve issues."""

from __future__ import annotations

import uuid as _uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.asset import Asset
from shared.models.frame_spec import FrameSpec
from shared.models.job import Job
from shared.models.provider_run import ProviderRun
from shared.models.qa_result import QAResult
from shared.models.scene import Scene
from shared.models.script_version import ScriptVersion
from shared.models.shot import Shot
from shared.models.subtitle_track import SubtitleTrack
from shared.models.timeline import Timeline
from shared.models.voice_track import VoiceTrack
from shared.qa.engine import run_all_checks
from shared.qa.rules import QAContext, SceneContext, ShotContext
from shared.schemas.qa import (
    QAIssue,
    QAListResponse,
    QAResultResponse,
    QARunRequest,
    QARunResponse,
    QASummary,
)

router = APIRouter()


async def _build_context(
    db: AsyncSession,
    project_id: UUID,
    script_version_id: UUID | None,
) -> QAContext:
    """Build QAContext by fetching all relevant data from DB."""

    svid = script_version_id
    if not svid:
        sv = (
            await db.execute(
                select(ScriptVersion)
                .where(ScriptVersion.project_id == project_id)
                .order_by(ScriptVersion.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        svid = sv.id if sv else None

    target_dur: float | None = None
    if svid:
        sv_row = (
            await db.execute(select(ScriptVersion).where(ScriptVersion.id == svid))
        ).scalar_one_or_none()
        if sv_row and sv_row.input_params:
            target_dur = sv_row.input_params.get("duration_sec")

    scene_contexts: list[SceneContext] = []
    if svid:
        scenes_result = await db.execute(
            select(Scene).where(Scene.script_version_id == svid).order_by(Scene.order_index)
        )
        scenes = list(scenes_result.scalars().all())

        for scene in scenes:
            shots_result = await db.execute(
                select(Shot).where(Shot.scene_id == scene.id).order_by(Shot.order_index)
            )
            shots = list(shots_result.scalars().all())

            shot_contexts: list[ShotContext] = []
            for shot in shots:
                fs_result = await db.execute(
                    select(FrameSpec).where(FrameSpec.shot_id == shot.id).order_by(FrameSpec.order_index)
                )
                frame_specs = [
                    {"id": str(f.id), "frame_role": f.frame_role, "status": f.status}
                    for f in fs_result.scalars().all()
                ]

                img_result = await db.execute(
                    select(Asset).where(
                        Asset.parent_id == shot.id,
                        Asset.asset_type == "image",
                    )
                )
                image_assets_shot = [{"id": str(a.id), "status": a.status} for a in img_result.scalars().all()]

                fs_ids = [f["id"] for f in frame_specs]
                if fs_ids:
                    img_fs_result = await db.execute(
                        select(Asset).where(
                            Asset.parent_type == "frame_spec",
                            Asset.parent_id.in_([_uuid.UUID(fid) for fid in fs_ids]),
                            Asset.asset_type == "image",
                        )
                    )
                    for a in img_fs_result.scalars().all():
                        image_assets_shot.append({"id": str(a.id), "status": a.status})

                vid_result = await db.execute(
                    select(Asset).where(
                        Asset.parent_type == "shot",
                        Asset.parent_id == shot.id,
                        Asset.asset_type == "video",
                    )
                )
                video_assets = [{"id": str(a.id), "status": a.status} for a in vid_result.scalars().all()]

                vt_result = await db.execute(
                    select(VoiceTrack).where(VoiceTrack.shot_id == shot.id)
                )
                voice_tracks = [{"id": str(v.id), "status": v.status} for v in vt_result.scalars().all()]

                shot_contexts.append(ShotContext(
                    shot_id=str(shot.id),
                    scene_id=str(scene.id),
                    order_index=shot.order_index,
                    duration_sec=shot.duration_sec,
                    status=shot.status,
                    narration_segment=shot.narration_segment,
                    asset_strategy=shot.asset_strategy,
                    frame_specs=frame_specs,
                    image_assets=image_assets_shot,
                    video_assets=video_assets,
                    voice_tracks=voice_tracks,
                ))

            scene_contexts.append(SceneContext(
                scene_id=str(scene.id),
                order_index=scene.order_index,
                duration_estimate_sec=scene.duration_estimate_sec,
                status=scene.status,
                narration_text=scene.narration_text,
                shots=shot_contexts,
            ))

    sub_result = await db.execute(
        select(SubtitleTrack).where(SubtitleTrack.project_id == project_id).order_by(SubtitleTrack.created_at.desc())
    )
    subtitle_tracks = [
        {"id": str(s.id), "status": s.status, "total_segments": s.total_segments, "total_duration_ms": s.total_duration_ms}
        for s in sub_result.scalars().all()
    ]

    tl_result = await db.execute(
        select(Timeline).where(Timeline.project_id == project_id).order_by(Timeline.created_at.desc())
    )
    timelines = [{"id": str(t.id), "status": t.status} for t in tl_result.scalars().all()]

    failed_jobs_result = await db.execute(
        select(Job).where(
            Job.project_id == project_id,
            Job.status == "failed",
        ).order_by(Job.created_at.desc()).limit(50)
    )
    failed_jobs = [{"id": str(j.id), "job_type": j.job_type, "error_message": j.error_message} for j in failed_jobs_result.scalars().all()]

    failed_pr_result = await db.execute(
        select(ProviderRun).where(
            ProviderRun.project_id == project_id,
            ProviderRun.status == "failed",
        ).order_by(ProviderRun.created_at.desc()).limit(50)
    )
    failed_provider_runs = [{"id": str(p.id), "provider_name": p.provider} for p in failed_pr_result.scalars().all()]

    return QAContext(
        project_id=str(project_id),
        script_version_id=str(svid) if svid else None,
        target_duration_sec=target_dur,
        scenes=scene_contexts,
        subtitle_tracks=subtitle_tracks,
        timelines=timelines,
        failed_jobs=failed_jobs,
        failed_provider_runs=failed_provider_runs,
    )


@router.post(
    "/{project_id}/qa/run",
    response_model=QARunResponse,
)
async def run_qa(
    project_id: UUID,
    body: QARunRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Run QA checks and persist results. Previous unresolved results are cleared."""
    req = body or QARunRequest()

    svid: UUID | None = None
    if req.script_version_id:
        svid = UUID(req.script_version_id)

    ctx = await _build_context(db, project_id, svid)

    issues: list[QAIssue] = run_all_checks(ctx, only_checks=req.checks)

    await db.execute(
        delete(QAResult).where(
            QAResult.project_id == project_id,
            QAResult.resolved == False,  # noqa: E712
        )
    )

    for issue in issues:
        qa = QAResult(
            project_id=project_id,
            script_version_id=svid,
            scope=issue.scope,
            target_type=issue.target_type,
            target_id=_uuid.UUID(issue.target_id) if issue.target_id else None,
            check_type=issue.check_type,
            severity=issue.severity,
            message=issue.message,
            details=issue.details,
            suggestion=issue.suggestion,
            source=issue.source,
        )
        db.add(qa)

    await db.flush()

    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    infos = sum(1 for i in issues if i.severity == "info")

    return QARunResponse(
        total_issues=len(issues),
        errors=errors,
        warnings=warnings,
        infos=infos,
        render_ready=errors == 0,
    )


@router.get(
    "/{project_id}/qa",
    response_model=QAListResponse,
)
async def list_qa_results(
    project_id: UUID,
    severity: str | None = Query(None, pattern=r"^(error|warning|info)$"),
    scope: str | None = Query(None, pattern=r"^(project|scene|shot|frame)$"),
    resolved: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List QA results with optional filters."""
    q = select(QAResult).where(QAResult.project_id == project_id)

    if severity:
        q = q.where(QAResult.severity == severity)
    if scope:
        q = q.where(QAResult.scope == scope)
    if resolved is not None:
        q = q.where(QAResult.resolved == resolved)

    q = q.order_by(QAResult.created_at.desc())

    result = await db.execute(q)
    items = list(result.scalars().all())
    items.sort(key=lambda x: {"error": 0, "warning": 1, "info": 2}.get(x.severity, 3))

    return QAListResponse(results=items, total=len(items))


@router.get(
    "/{project_id}/qa/summary",
    response_model=QASummary,
)
async def qa_summary(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get QA summary for a project (unresolved issues only)."""
    result = await db.execute(
        select(QAResult).where(
            QAResult.project_id == project_id,
            QAResult.resolved == False,  # noqa: E712
        )
    )
    items = list(result.scalars().all())

    errors = [i for i in items if i.severity == "error"]
    warnings = [i for i in items if i.severity == "warning"]
    infos = [i for i in items if i.severity == "info"]

    by_check_type: dict[str, int] = {}
    by_scope: dict[str, int] = {}
    for i in items:
        by_check_type[i.check_type] = by_check_type.get(i.check_type, 0) + 1
        by_scope[i.scope] = by_scope.get(i.scope, 0) + 1

    blocking = sorted(errors, key=lambda x: x.created_at)

    return QASummary(
        total=len(items),
        errors=len(errors),
        warnings=len(warnings),
        infos=len(infos),
        by_check_type=by_check_type,
        by_scope=by_scope,
        render_ready=len(errors) == 0,
        blocking_issues=blocking,
    )


@router.patch(
    "/{project_id}/qa/{qa_id}/resolve",
)
async def resolve_qa_result(
    project_id: UUID,
    qa_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Mark a QA result as resolved."""
    qa = (
        await db.execute(select(QAResult).where(QAResult.id == qa_id))
    ).scalar_one_or_none()
    if not qa:
        raise HTTPException(404, "QA result not found")
    if qa.project_id != project_id:
        raise HTTPException(404, "QA result not found in this project")

    qa.resolved = True
    await db.flush()
    return {"id": str(qa.id), "resolved": True}


@router.delete(
    "/{project_id}/qa/clear",
)
async def clear_qa_results(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Clear all QA results for a project."""
    result = await db.execute(
        delete(QAResult).where(QAResult.project_id == project_id)
    )
    return {"deleted": result.rowcount}
