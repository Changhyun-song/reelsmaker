import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import get_settings
from shared.database import get_db
from app.auth import get_current_user
from app.api.projects import router as projects_router
from app.api.jobs import router as jobs_router
from app.api.scripts import router as scripts_router
from app.api.scenes import router as scenes_router
from app.api.shots import router as shots_router
from app.api.frames import router as frames_router
from app.api.style_presets import router as style_presets_router
from app.api.characters import router as characters_router
from app.api.prompts import router as prompts_router
from app.api.images import router as images_router
from app.api.videos import router as videos_router
from app.api.tts import router as tts_router
from app.api.subtitles import router as subtitles_router
from app.api.timelines import router as timelines_router
from app.api.renders import router as renders_router
from app.api.selection import router as selection_router
from app.api.qa import router as qa_router
from app.api.exports import router as exports_router
from app.api.evaluations import router as evaluations_router
from app.api.continuity import router as continuity_router
from app.api.prompt_history import router as prompt_history_router
from app.api.ops import router as ops_router
from app.api.billing import router as billing_router

settings = get_settings()
api_router = APIRouter()
api_router.include_router(ops_router, prefix="/ops", tags=["ops"])
api_router.include_router(billing_router, prefix="/billing", tags=["billing"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
api_router.include_router(scripts_router, prefix="/projects", tags=["scripts"])
api_router.include_router(scenes_router, prefix="/projects", tags=["scenes"])
api_router.include_router(shots_router, prefix="/projects", tags=["shots"])
api_router.include_router(frames_router, prefix="/projects", tags=["frames"])
api_router.include_router(style_presets_router, prefix="/projects", tags=["styles"])
api_router.include_router(characters_router, prefix="/projects", tags=["characters"])
api_router.include_router(prompts_router, prefix="/projects", tags=["prompts"])
api_router.include_router(images_router, prefix="/projects", tags=["images"])
api_router.include_router(videos_router, prefix="/projects", tags=["videos"])
api_router.include_router(tts_router, prefix="/projects", tags=["tts"])
api_router.include_router(subtitles_router, prefix="/projects", tags=["subtitles"])
api_router.include_router(timelines_router, prefix="/projects", tags=["timelines"])
api_router.include_router(renders_router, prefix="/projects", tags=["render"])
api_router.include_router(selection_router, prefix="/projects", tags=["selection"])
api_router.include_router(qa_router, prefix="/projects", tags=["qa"])
api_router.include_router(exports_router, prefix="/projects", tags=["export"])
api_router.include_router(evaluations_router, prefix="/projects", tags=["evaluations"])
api_router.include_router(continuity_router, prefix="/projects", tags=["continuity"])
api_router.include_router(prompt_history_router, prefix="/projects", tags=["prompt-history"])


# ── Continuity Bible CRUD (stored in project.settings.bible) ──


@api_router.get("/projects/{project_id}/bible", tags=["projects"])
async def get_bible(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get the Continuity Bible for a project."""
    from shared.models.project import Project
    from sqlalchemy import select as sel
    project = (await db.execute(sel(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    bible = (project.settings or {}).get("bible", {})
    return {
        "project_id": project_id,
        "bible": bible,
        "fields": [
            {"key": "main_subject_identity", "label": "주인공/주체 정체성", "hint": "전체 영상에 등장하는 주요 인물이나 대상의 시각적 특징"},
            {"key": "character_visual_rules", "label": "캐릭터 시각 규칙", "hint": "캐릭터 외형이 씬마다 흔들리지 않도록 고정할 규칙"},
            {"key": "wardrobe_rules", "label": "의상/소품 규칙", "hint": "의상, 액세서리, 소품이 씬마다 달라지지 않도록 고정"},
            {"key": "palette_rules", "label": "색감/팔레트 규칙", "hint": "전체 영상의 색감 톤, 주요 컬러 팔레트"},
            {"key": "lighting_rules", "label": "조명 규칙", "hint": "조명 방향, 색온도, 질감이 일관되도록"},
            {"key": "lens_rules", "label": "렌즈/카메라 톤", "hint": "렌즈 느낌, 피사계심도, 카메라 스타일"},
            {"key": "environment_consistency_rules", "label": "환경 일관성", "hint": "배경, 장소, 날씨, 시간대가 씬 간 일관되도록"},
            {"key": "forbidden_drift_rules", "label": "변하면 안 되는 것", "hint": "절대 변하면 안 되는 요소 (예: 캐릭터 머리색, 시간대)"},
        ],
    }


@api_router.put("/projects/{project_id}/bible", tags=["projects"])
async def update_bible(
    project_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Update the Continuity Bible for a project."""
    from shared.models.project import Project
    from sqlalchemy import select as sel
    project = (await db.execute(sel(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    allowed_keys = {
        "main_subject_identity", "character_visual_rules", "wardrobe_rules",
        "palette_rules", "lighting_rules", "lens_rules",
        "environment_consistency_rules", "forbidden_drift_rules",
    }
    bible_data = {k: v for k, v in body.get("bible", body).items() if k in allowed_keys}

    settings = dict(project.settings or {})
    settings["bible"] = bible_data
    project.settings = settings

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(project, "settings")
    await db.flush()
    await db.refresh(project)

    return {"project_id": project_id, "bible": bible_data, "saved": True}


@api_router.get("/projects/{project_id}/progress", tags=["projects"])
async def project_progress(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Return pipeline completion status for each stage."""
    from shared.models import (
        ScriptVersion, Scene, Shot, FrameSpec, Asset,
        VoiceTrack, SubtitleTrack, Timeline, RenderJob, Job,
    )
    from sqlalchemy import func, select

    sv = await db.execute(
        select(ScriptVersion.id, ScriptVersion.status)
        .where(ScriptVersion.project_id == project_id)
        .order_by(ScriptVersion.version.desc())
        .limit(1)
    )
    script_row = sv.first()
    script_id = script_row[0] if script_row else None
    has_script = script_row is not None and script_row[1] in ("planned", "structured")

    scene_count = 0
    shot_count = 0
    frame_count = 0
    if script_id:
        scene_count = (await db.execute(
            select(func.count()).where(Scene.script_version_id == script_id)
        )).scalar() or 0
        if scene_count > 0:
            scene_ids = [r[0] for r in (await db.execute(
                select(Scene.id).where(Scene.script_version_id == script_id)
            )).all()]
            shot_count = (await db.execute(
                select(func.count()).where(Shot.scene_id.in_(scene_ids))
            )).scalar() or 0
            if shot_count > 0:
                shot_ids = [r[0] for r in (await db.execute(
                    select(Shot.id).where(Shot.scene_id.in_(scene_ids))
                )).all()]
                frame_count = (await db.execute(
                    select(func.count()).where(FrameSpec.shot_id.in_(shot_ids))
                )).scalar() or 0

    image_count = (await db.execute(
        select(func.count()).where(Asset.project_id == project_id, Asset.asset_type == "image")
    )).scalar() or 0

    video_count = (await db.execute(
        select(func.count()).where(Asset.project_id == project_id, Asset.asset_type == "video")
    )).scalar() or 0

    voice_count = (await db.execute(
        select(func.count()).where(VoiceTrack.project_id == project_id)
    )).scalar() or 0

    subtitle_count = (await db.execute(
        select(func.count()).where(SubtitleTrack.project_id == project_id)
    )).scalar() or 0

    timeline_count = (await db.execute(
        select(func.count()).where(Timeline.project_id == project_id)
    )).scalar() or 0

    render_completed = (await db.execute(
        select(func.count()).where(
            RenderJob.project_id == project_id, RenderJob.status == "completed"
        )
    )).scalar() or 0

    running_jobs = (await db.execute(
        select(Job.id, Job.job_type, Job.status, Job.progress)
        .where(Job.project_id == project_id, Job.status.in_(["queued", "running"]))
        .order_by(Job.created_at.desc())
        .limit(5)
    )).all()

    active_jobs = [
        {"id": str(j[0]), "job_type": j[1], "status": j[2], "progress": j[3]}
        for j in running_jobs
    ]

    return {
        "script": has_script,
        "scenes": scene_count,
        "shots": shot_count,
        "frames": frame_count,
        "images": image_count,
        "videos": video_count,
        "voices": voice_count,
        "subtitles": subtitle_count,
        "timelines": timeline_count,
        "renders": render_completed,
        "active_jobs": active_jobs,
    }


@api_router.get("/projects/{project_id}/pipeline-inspect", tags=["projects"])
async def pipeline_inspect(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Full pipeline diagnostic snapshot for a project."""
    from shared.models import (
        ScriptVersion, Scene, Shot, FrameSpec, Asset,
        VoiceTrack, SubtitleTrack, Timeline, RenderJob, Job,
    )
    from shared.models.provider_run import ProviderRun
    from sqlalchemy import func, select, desc

    pid = project_id
    stages: dict = {}

    # ── Script ──
    sv_row = (await db.execute(
        select(
            ScriptVersion.id, ScriptVersion.status, ScriptVersion.version,
            ScriptVersion.created_at, ScriptVersion.updated_at,
        )
        .where(ScriptVersion.project_id == pid)
        .order_by(ScriptVersion.version.desc())
        .limit(1)
    )).first()
    script_id = sv_row[0] if sv_row else None
    stages["script"] = {
        "exists": sv_row is not None,
        "status": sv_row[1] if sv_row else None,
        "version": sv_row[2] if sv_row else None,
        "updated_at": str(sv_row[4] or sv_row[3]) if sv_row else None,
    }

    # ── Scene / Shot / Frame counts + structural warnings ──
    scene_count = shot_count = frame_count = 0
    scene_ids: list = []
    shot_ids: list = []
    frames_with_prompt = 0
    frames_with_story_prompt = 0

    if script_id:
        scene_count = (await db.execute(
            select(func.count()).where(Scene.script_version_id == script_id)
        )).scalar() or 0
        if scene_count > 0:
            scene_ids = [r[0] for r in (await db.execute(
                select(Scene.id).where(Scene.script_version_id == script_id)
            )).all()]
            shot_count = (await db.execute(
                select(func.count()).where(Shot.scene_id.in_(scene_ids))
            )).scalar() or 0
            if shot_count > 0:
                shot_ids = [r[0] for r in (await db.execute(
                    select(Shot.id).where(Shot.scene_id.in_(scene_ids))
                )).all()]
                frame_count = (await db.execute(
                    select(func.count()).where(FrameSpec.shot_id.in_(shot_ids))
                )).scalar() or 0
                frames_with_prompt = (await db.execute(
                    select(func.count()).where(
                        FrameSpec.shot_id.in_(shot_ids),
                        FrameSpec.visual_prompt.isnot(None),
                        FrameSpec.visual_prompt != "",
                    )
                )).scalar() or 0

    warnings: list[str] = []
    if scene_count > 0 and shot_count == 0:
        warnings.append("씬은 있지만 샷이 0개 — 샷 구성이 실행되지 않았습니다")
    if shot_count > 0 and frame_count == 0:
        warnings.append("샷은 있지만 프레임이 0개 — 프레임 구성이 실행되지 않았습니다")
    if frame_count > 0 and frames_with_prompt == 0:
        warnings.append("프레임은 있지만 프롬프트가 0개 — 스토리 프롬프트 또는 이미지 생성을 실행하세요")

    stages["scene"] = {"count": scene_count, "updated_at": None}
    stages["shot"] = {"count": shot_count, "updated_at": None}
    stages["frame"] = {
        "count": frame_count,
        "with_prompt": frames_with_prompt,
        "story_prompt_ratio": f"{frames_with_prompt}/{frame_count}" if frame_count else "0/0",
        "updated_at": None,
    }

    # ── Image / Video / TTS / Subtitle / Timeline / Render ──
    image_count = (await db.execute(
        select(func.count()).where(Asset.project_id == pid, Asset.asset_type == "image")
    )).scalar() or 0
    image_ready = (await db.execute(
        select(func.count()).where(Asset.project_id == pid, Asset.asset_type == "image", Asset.status == "ready")
    )).scalar() or 0

    video_count = (await db.execute(
        select(func.count()).where(Asset.project_id == pid, Asset.asset_type == "video")
    )).scalar() or 0
    video_ready = (await db.execute(
        select(func.count()).where(Asset.project_id == pid, Asset.asset_type == "video", Asset.status == "ready")
    )).scalar() or 0

    voice_count = (await db.execute(
        select(func.count()).where(VoiceTrack.project_id == pid)
    )).scalar() or 0
    subtitle_count = (await db.execute(
        select(func.count()).where(SubtitleTrack.project_id == pid)
    )).scalar() or 0
    timeline_count = (await db.execute(
        select(func.count()).where(Timeline.project_id == pid)
    )).scalar() or 0
    render_count = (await db.execute(
        select(func.count()).where(RenderJob.project_id == pid)
    )).scalar() or 0
    render_completed = (await db.execute(
        select(func.count()).where(RenderJob.project_id == pid, RenderJob.status == "completed")
    )).scalar() or 0

    stages["image"] = {"total": image_count, "ready": image_ready}
    stages["video"] = {"total": video_count, "ready": video_ready}
    stages["tts"] = {"count": voice_count}
    stages["subtitle"] = {"count": subtitle_count}
    stages["timeline"] = {"count": timeline_count}
    stages["render"] = {"total": render_count, "completed": render_completed}

    # ── Recent jobs (last 20, all statuses) ──
    recent_jobs_rows = (await db.execute(
        select(
            Job.id, Job.job_type, Job.status, Job.progress,
            Job.error_message, Job.created_at, Job.completed_at,
            Job.result, Job.retry_count, Job.max_retries,
        )
        .where(Job.project_id == pid)
        .order_by(desc(Job.created_at))
        .limit(20)
    )).all()

    recent_jobs = []
    latest_by_type: dict[str, dict] = {}
    for j in recent_jobs_rows:
        jd = {
            "id": str(j[0]), "job_type": j[1], "status": j[2],
            "progress": j[3], "error_message": j[4],
            "created_at": str(j[5]) if j[5] else None,
            "completed_at": str(j[6]) if j[6] else None,
            "result_preview": _truncate_dict(j[7], 300) if j[7] else None,
            "retry_count": j[8], "max_retries": j[9],
        }
        recent_jobs.append(jd)
        if j[1] not in latest_by_type:
            latest_by_type[j[1]] = jd

    # ── Provider runs (recent 10) ──
    provider_rows = (await db.execute(
        select(
            ProviderRun.provider, ProviderRun.operation, ProviderRun.model,
            ProviderRun.status, ProviderRun.latency_ms, ProviderRun.error_message,
            ProviderRun.created_at, ProviderRun.cost_estimate,
        )
        .where(ProviderRun.project_id == pid)
        .order_by(desc(ProviderRun.created_at))
        .limit(10)
    )).all()

    provider_runs = [
        {
            "provider": r[0], "operation": r[1], "model": r[2],
            "status": r[3], "latency_ms": r[4], "error_message": r[5],
            "created_at": str(r[6]) if r[6] else None,
            "cost_estimate": r[7],
        }
        for r in provider_rows
    ]

    # ── Prompt samples (first 3 frames that have visual_prompt) ──
    prompt_samples = []
    if frame_count > 0 and shot_ids:
        sample_frames = (await db.execute(
            select(FrameSpec.id, FrameSpec.frame_role, FrameSpec.visual_prompt, FrameSpec.negative_prompt)
            .where(FrameSpec.shot_id.in_(shot_ids), FrameSpec.visual_prompt.isnot(None))
            .order_by(FrameSpec.order_index)
            .limit(3)
        )).all()
        for sf in sample_frames:
            prompt_samples.append({
                "frame_id": str(sf[0]),
                "frame_role": sf[1],
                "visual_prompt_preview": (sf[2] or "")[:300],
                "has_negative": bool(sf[3]),
            })

    # ── Health / providers info ──
    providers = {
        "image": settings.image_provider,
        "video": settings.video_provider,
        "tts": settings.tts_provider,
        "text": "claude" if settings.anthropic_api_key else "none",
    }

    return {
        "project_id": pid,
        "stages": stages,
        "warnings": warnings,
        "recent_jobs": recent_jobs,
        "latest_by_type": latest_by_type,
        "provider_runs": provider_runs,
        "prompt_samples": prompt_samples,
        "providers": providers,
    }


def _truncate_dict(d: dict | None, max_chars: int = 300) -> dict | str:
    if not d:
        return {}
    import json
    s = json.dumps(d, ensure_ascii=False, default=str)
    if len(s) > max_chars:
        return s[:max_chars] + "..."
    return d


@api_router.get("/health", tags=["system"])
async def health_check(db: AsyncSession = Depends(get_db)):
    checks: dict[str, str] = {"api": "ok"}

    try:
        await db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    try:
        from app.services.storage import s3_client
        s3_client.head_bucket(Bucket=settings.s3_bucket)
        checks["storage"] = "ok"
    except Exception as e:
        checks["storage"] = f"error: {e}"

    checks["providers"] = {
        "image": settings.image_provider,
        "video": settings.video_provider,
        "tts": settings.tts_provider,
        "text": "claude" if settings.anthropic_api_key else "none",
    }

    all_ok = all(v == "ok" for k, v in checks.items() if k != "providers")
    return {"status": "ok" if all_ok else "degraded", "services": checks}


@api_router.get("/diagnostics", tags=["system"])
async def diagnostics(db: AsyncSession = Depends(get_db)):
    """Production deployment diagnostics with fail-fast rules."""
    from shared.models.job import Job
    from sqlalchemy import func, select, desc
    from datetime import datetime, timezone, timedelta
    import os

    errors: list[dict] = []
    warnings: list[dict] = []

    def _add(level: str, code: str, msg: str, hint: str = ""):
        entry = {"code": code, "message": msg}
        if hint:
            entry["hint"] = hint
        (errors if level == "error" else warnings).append(entry)

    # ── 1. Connectivity checks ──
    conn: dict[str, dict] = {}

    # DB
    try:
        await db.execute(text("SELECT 1"))
        conn["postgres"] = {"status": "ok"}
    except Exception as e:
        conn["postgres"] = {"status": "error", "error": str(e)[:200]}
        _add("error", "DB_UNREACHABLE", "PostgreSQL 연결 실패",
             "DATABASE_URL 환경변수를 확인하세요. SSL 파라미터가 asyncpg와 호환되는지 확인하세요.")

    # Redis
    redis_ok = False
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        conn["redis"] = {"status": "ok"}
        redis_ok = True
    except Exception as e:
        conn["redis"] = {"status": "error", "error": str(e)[:200]}
        _add("error", "REDIS_UNREACHABLE", "Redis 연결 실패",
             "REDIS_URL 환경변수를 확인하세요. Railway에서는 Redis 플러그인이 필요합니다.")

    # Storage
    storage_ok = False
    try:
        from app.services.storage import s3_client
        s3_client.head_bucket(Bucket=settings.s3_bucket)
        conn["storage"] = {"status": "ok", "bucket": settings.s3_bucket}
        storage_ok = True
    except Exception as e:
        conn["storage"] = {"status": "error", "error": str(e)[:200]}
        _add("error", "STORAGE_UNREACHABLE", f"Object Storage 연결 실패 (bucket: {settings.s3_bucket})",
             "S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY를 확인하세요. R2의 경우 bucket 권한도 확인하세요.")

    # ── 2. Provider config checks ──
    providers: dict[str, dict] = {}

    provider_key_map = {
        "image": {
            "fal": ("fal_key", "FAL_KEY"),
            "openai": ("openai_api_key", "OPENAI_API_KEY"),
            "gemini": ("google_api_key", "GOOGLE_API_KEY"),
            "higgsfield": ("higgsfield_api_key_id", "HIGGSFIELD_API_KEY_ID"),
        },
        "video": {
            "runway": ("runway_api_key", "RUNWAY_API_KEY"),
            "kling": ("fal_key", "FAL_KEY"),
            "luma": ("luma_api_key", "LUMA_API_KEY"),
            "higgsfield": ("higgsfield_api_key_id", "HIGGSFIELD_API_KEY_ID"),
            "seedance": ("fal_key", "FAL_KEY"),
        },
        "tts": {
            "elevenlabs": ("elevenlabs_api_key", "ELEVENLABS_API_KEY"),
        },
    }

    for ptype, pname in [("image", settings.image_provider), ("video", settings.video_provider), ("tts", settings.tts_provider)]:
        is_mock = pname == "mock"
        has_key = True
        key_env = None

        if not is_mock and pname in provider_key_map.get(ptype, {}):
            attr, key_env = provider_key_map[ptype][pname]
            has_key = bool(getattr(settings, attr, ""))

        providers[ptype] = {
            "provider": pname,
            "mode": "mock" if is_mock else "real",
            "api_key_set": has_key if not is_mock else None,
        }

        if not is_mock and not has_key:
            _add("error", f"{ptype.upper()}_KEY_MISSING",
                 f"{ptype} provider가 '{pname}'인데 API 키가 없습니다",
                 f"{key_env} 환경변수를 설정하세요.")

    text_key = bool(settings.anthropic_api_key)
    providers["text"] = {
        "provider": "claude" if text_key else "none",
        "mode": "real" if text_key else "unavailable",
        "api_key_set": text_key,
    }
    if not text_key:
        _add("error", "TEXT_KEY_MISSING", "Claude(Anthropic) API 키가 없습니다 — AI 기능 전체 불가",
             "ANTHROPIC_API_KEY 환경변수를 설정하세요.")

    # ── 3. Environment & CORS checks ──
    env_info: dict = {
        "debug": settings.debug,
        "cors_origins": settings.cors_origins,
        "s3_public_endpoint_set": bool(settings.s3_public_endpoint),
        "auth_enabled": settings.auth_enabled,
    }

    is_production = not settings.debug or os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("VERCEL")

    if is_production:
        if not settings.s3_public_endpoint:
            _add("warn", "S3_PUBLIC_MISSING",
                 "S3_PUBLIC_ENDPOINT가 설정되지 않음 — presigned URL이 내부 주소를 참조할 수 있습니다",
                 "S3_PUBLIC_ENDPOINT를 공개 접근 가능한 URL로 설정하세요.")

        s3_ep = settings.s3_endpoint
        if "localhost" in s3_ep or "127.0.0.1" in s3_ep or "minio" in s3_ep:
            _add("warn", "S3_LOCALHOST",
                 f"S3_ENDPOINT가 로컬 주소입니다: {_mask(s3_ep)}",
                 "프로덕션에서는 Cloudflare R2 등 외부 스토리지 URL을 사용하세요.")

        db_url = settings.database_url
        if "localhost" in db_url or "127.0.0.1" in db_url:
            _add("warn", "DB_LOCALHOST",
                 "DATABASE_URL이 localhost를 가리킵니다",
                 "프로덕션에서는 Neon/Supabase 등 외부 DB URL을 사용하세요.")

        redis_url = settings.redis_url
        if "localhost" in redis_url or "127.0.0.1" in redis_url:
            _add("warn", "REDIS_LOCALHOST",
                 "REDIS_URL이 localhost를 가리킵니다",
                 "프로덕션에서는 Railway Redis 등 외부 Redis URL을 사용하세요.")

    # ── 4. Worker heartbeat check ──
    worker: dict = {"status": "unknown"}
    if redis_ok:
        try:
            now = datetime.now(timezone.utc)
            five_min_ago = now - timedelta(minutes=5)
            recent_completed = (await db.execute(
                select(func.count())
                .where(
                    Job.status == "completed",
                    Job.completed_at >= five_min_ago,
                )
            )).scalar() or 0

            stuck_queued = (await db.execute(
                select(func.count())
                .where(
                    Job.status == "queued",
                    Job.created_at <= five_min_ago,
                )
            )).scalar() or 0

            if recent_completed > 0:
                worker["status"] = "active"
                worker["recent_completed"] = recent_completed
            elif stuck_queued > 0:
                worker["status"] = "possibly_down"
                worker["stuck_queued"] = stuck_queued
                _add("warn", "WORKER_STUCK",
                     f"{stuck_queued}개 작업이 5분 이상 queued 상태입니다 — Worker가 작동하지 않을 수 있습니다",
                     "Worker 서비스 로그를 확인하세요. Railway에서 Worker 서비스가 정상 배포되었는지 확인하세요.")
            else:
                worker["status"] = "idle"
        except Exception:
            worker["status"] = "check_failed"
    else:
        worker["status"] = "redis_unavailable"

    # ── 5. Required env summary ──
    required_env = {
        "DATABASE_URL": bool(settings.database_url and "localhost" not in settings.database_url) if is_production else True,
        "REDIS_URL": bool(settings.redis_url and "localhost" not in settings.redis_url) if is_production else True,
        "ANTHROPIC_API_KEY": bool(settings.anthropic_api_key),
        "S3_ENDPOINT": bool(settings.s3_endpoint),
        "S3_ACCESS_KEY": bool(settings.s3_access_key and settings.s3_access_key != "minioadmin"),
        "S3_SECRET_KEY": bool(settings.s3_secret_key and settings.s3_secret_key != "minioadmin"),
        "S3_PUBLIC_ENDPOINT": bool(settings.s3_public_endpoint),
    }

    total_errors = len(errors)
    total_warnings = len(warnings)
    overall = "healthy" if total_errors == 0 and total_warnings == 0 else \
              "degraded" if total_errors == 0 else "unhealthy"

    return {
        "overall": overall,
        "is_production": is_production,
        "errors": errors,
        "warnings": warnings,
        "connectivity": conn,
        "providers": providers,
        "worker": worker,
        "environment": env_info,
        "required_env": required_env,
        "error_count": total_errors,
        "warning_count": total_warnings,
    }


def _mask(value: str) -> str:
    """Show structure of URL without exposing secrets."""
    from urllib.parse import urlparse
    try:
        p = urlparse(value)
        host = p.hostname or ""
        port = f":{p.port}" if p.port else ""
        return f"{p.scheme}://{host}{port}/..."
    except Exception:
        return value[:20] + "..."
