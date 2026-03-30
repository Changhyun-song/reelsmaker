"""Operations observability API — provider stats, job stats, project summaries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.job import Job
from shared.models.provider_run import ProviderRun

router = APIRouter()


# ── Response schemas ─────────────────────────────────

class RecentJob(BaseModel):
    id: str
    job_type: str
    status: str
    progress: int
    duration_sec: float | None
    error_message: str | None
    project_id: str | None
    created_at: str


class ProviderStats(BaseModel):
    provider: str
    total_runs: int
    success: int
    failed: int
    success_rate: float
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    total_cost: float | None
    total_input_tokens: int
    total_output_tokens: int


class CategoryStats(BaseModel):
    operation: str
    total_runs: int
    success: int
    failed: int
    failure_rate: float
    avg_latency_ms: float | None


class JobTypeStats(BaseModel):
    job_type: str
    total: int
    completed: int
    failed: int
    avg_duration_sec: float | None
    failure_rate: float


class ProjectSummary(BaseModel):
    project_id: str
    provider_runs: int
    total_cost: float | None
    total_latency_sec: float | None
    total_jobs: int
    completed_jobs: int
    failed_jobs: int


class OpsResponse(BaseModel):
    recent_jobs: list[RecentJob]
    provider_stats: list[ProviderStats]
    category_stats: list[CategoryStats]
    job_type_stats: list[JobTypeStats]
    project_summaries: list[ProjectSummary]
    period_days: int


# ── Main endpoint ────────────────────────────────────

@router.get("/stats", response_model=OpsResponse)
async def ops_stats(
    days: int = Query(7, ge=1, le=90, description="Lookback window in days"),
    project_id: UUID | None = Query(None, description="Filter to a single project"),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    recent_jobs = await _recent_jobs(db, since, project_id)
    provider_stats = await _provider_stats(db, since, project_id)
    category_stats = await _category_stats(db, since, project_id)
    job_type_stats = await _job_type_stats(db, since, project_id)
    project_summaries = await _project_summaries(db, since, project_id)

    return OpsResponse(
        recent_jobs=recent_jobs,
        provider_stats=provider_stats,
        category_stats=category_stats,
        job_type_stats=job_type_stats,
        project_summaries=project_summaries,
        period_days=days,
    )


# ── Helpers ──────────────────────────────────────────

async def _recent_jobs(
    db: AsyncSession, since: datetime, project_id: UUID | None,
) -> list[RecentJob]:
    q = select(Job).where(Job.created_at >= since)
    if project_id:
        q = q.where(Job.project_id == project_id)
    q = q.order_by(Job.created_at.desc()).limit(20)

    result = await db.execute(q)
    rows: list[RecentJob] = []
    for j in result.scalars().all():
        duration = None
        if j.started_at and j.completed_at:
            duration = round((j.completed_at - j.started_at).total_seconds(), 2)
        rows.append(RecentJob(
            id=str(j.id),
            job_type=j.job_type,
            status=j.status,
            progress=j.progress,
            duration_sec=duration,
            error_message=j.error_message[:200] if j.error_message else None,
            project_id=str(j.project_id) if j.project_id else None,
            created_at=j.created_at.isoformat() if j.created_at else "",
        ))
    return rows


async def _provider_stats(
    db: AsyncSession, since: datetime, project_id: UUID | None,
) -> list[ProviderStats]:
    q = (
        select(
            ProviderRun.provider,
            func.count().label("total"),
            func.sum(case((ProviderRun.status == "success", 1), else_=0)).label("ok"),
            func.sum(case((ProviderRun.status == "failed", 1), else_=0)).label("fail"),
            func.avg(ProviderRun.latency_ms).label("avg_lat"),
            func.percentile_cont(0.95).within_group(ProviderRun.latency_ms).label("p95_lat"),
            func.sum(ProviderRun.cost_estimate).label("cost"),
        )
        .where(ProviderRun.created_at >= since)
        .group_by(ProviderRun.provider)
        .order_by(func.count().desc())
    )
    if project_id:
        q = q.where(ProviderRun.project_id == project_id)

    result = await db.execute(q)
    rows: list[ProviderStats] = []
    for r in result.all():
        total = r.total or 0
        ok = r.ok or 0
        fail = r.fail or 0
        input_tok, output_tok = await _token_totals(db, since, r.provider, project_id)
        rows.append(ProviderStats(
            provider=r.provider,
            total_runs=total,
            success=ok,
            failed=fail,
            success_rate=round(ok / total * 100, 1) if total else 0,
            avg_latency_ms=round(float(r.avg_lat), 1) if r.avg_lat else None,
            p95_latency_ms=round(float(r.p95_lat), 1) if r.p95_lat else None,
            total_cost=round(float(r.cost), 6) if r.cost else None,
            total_input_tokens=input_tok,
            total_output_tokens=output_tok,
        ))
    return rows


async def _token_totals(
    db: AsyncSession,
    since: datetime,
    provider: str,
    project_id: UUID | None,
) -> tuple[int, int]:
    """Sum input/output tokens from JSONB token_usage column."""
    q = (
        select(
            func.sum(
                func.coalesce(
                    ProviderRun.token_usage["input_tokens"].as_integer(), 0
                )
            ).label("inp"),
            func.sum(
                func.coalesce(
                    ProviderRun.token_usage["output_tokens"].as_integer(), 0
                )
            ).label("out"),
        )
        .where(
            ProviderRun.created_at >= since,
            ProviderRun.provider == provider,
            ProviderRun.token_usage.isnot(None),
        )
    )
    if project_id:
        q = q.where(ProviderRun.project_id == project_id)

    result = await db.execute(q)
    row = result.one()
    return int(row.inp or 0), int(row.out or 0)


async def _category_stats(
    db: AsyncSession, since: datetime, project_id: UUID | None,
) -> list[CategoryStats]:
    q = (
        select(
            ProviderRun.operation,
            func.count().label("total"),
            func.sum(case((ProviderRun.status == "success", 1), else_=0)).label("ok"),
            func.sum(case((ProviderRun.status == "failed", 1), else_=0)).label("fail"),
            func.avg(ProviderRun.latency_ms).label("avg_lat"),
        )
        .where(ProviderRun.created_at >= since)
        .group_by(ProviderRun.operation)
        .order_by(func.count().desc())
    )
    if project_id:
        q = q.where(ProviderRun.project_id == project_id)

    result = await db.execute(q)
    rows: list[CategoryStats] = []
    for r in result.all():
        total = r.total or 0
        fail = r.fail or 0
        rows.append(CategoryStats(
            operation=r.operation,
            total_runs=total,
            success=r.ok or 0,
            failed=fail,
            failure_rate=round(fail / total * 100, 1) if total else 0,
            avg_latency_ms=round(float(r.avg_lat), 1) if r.avg_lat else None,
        ))
    return rows


async def _job_type_stats(
    db: AsyncSession, since: datetime, project_id: UUID | None,
) -> list[JobTypeStats]:
    duration_expr = func.extract(
        "epoch",
        Job.completed_at - Job.started_at,
    )

    q = (
        select(
            Job.job_type,
            func.count().label("total"),
            func.sum(case((Job.status == "completed", 1), else_=0)).label("ok"),
            func.sum(case((Job.status == "failed", 1), else_=0)).label("fail"),
            func.avg(
                case(
                    (Job.completed_at.isnot(None), duration_expr),
                    else_=None,
                )
            ).label("avg_dur"),
        )
        .where(Job.created_at >= since)
        .group_by(Job.job_type)
        .order_by(func.count().desc())
    )
    if project_id:
        q = q.where(Job.project_id == project_id)

    result = await db.execute(q)
    rows: list[JobTypeStats] = []
    for r in result.all():
        total = r.total or 0
        fail = r.fail or 0
        rows.append(JobTypeStats(
            job_type=r.job_type,
            total=total,
            completed=r.ok or 0,
            failed=fail,
            avg_duration_sec=round(float(r.avg_dur), 2) if r.avg_dur else None,
            failure_rate=round(fail / total * 100, 1) if total else 0,
        ))
    return rows


async def _project_summaries(
    db: AsyncSession, since: datetime, project_id: UUID | None,
) -> list[ProjectSummary]:
    pr_q = (
        select(
            ProviderRun.project_id,
            func.count().label("runs"),
            func.sum(ProviderRun.cost_estimate).label("cost"),
            func.sum(ProviderRun.latency_ms).label("lat_ms"),
        )
        .where(ProviderRun.created_at >= since)
        .group_by(ProviderRun.project_id)
    )
    if project_id:
        pr_q = pr_q.where(ProviderRun.project_id == project_id)

    job_q = (
        select(
            Job.project_id,
            func.count().label("total"),
            func.sum(case((Job.status == "completed", 1), else_=0)).label("ok"),
            func.sum(case((Job.status == "failed", 1), else_=0)).label("fail"),
        )
        .where(Job.created_at >= since, Job.project_id.isnot(None))
        .group_by(Job.project_id)
    )
    if project_id:
        job_q = job_q.where(Job.project_id == project_id)

    pr_result = await db.execute(pr_q)
    pr_map: dict[str, dict] = {}
    for r in pr_result.all():
        pid = str(r.project_id)
        pr_map[pid] = {
            "runs": r.runs or 0,
            "cost": round(float(r.cost), 6) if r.cost else None,
            "lat_sec": round(float(r.lat_ms) / 1000, 2) if r.lat_ms else None,
        }

    job_result = await db.execute(job_q)
    job_map: dict[str, dict] = {}
    for r in job_result.all():
        pid = str(r.project_id)
        job_map[pid] = {
            "total": r.total or 0,
            "ok": r.ok or 0,
            "fail": r.fail or 0,
        }

    all_pids = set(pr_map.keys()) | set(job_map.keys())
    rows: list[ProjectSummary] = []
    for pid in sorted(all_pids):
        pr = pr_map.get(pid, {"runs": 0, "cost": None, "lat_sec": None})
        jb = job_map.get(pid, {"total": 0, "ok": 0, "fail": 0})
        rows.append(ProjectSummary(
            project_id=pid,
            provider_runs=pr["runs"],
            total_cost=pr["cost"],
            total_latency_sec=pr["lat_sec"],
            total_jobs=jb["total"],
            completed_jobs=jb["ok"],
            failed_jobs=jb["fail"],
        ))

    rows.sort(key=lambda x: x.provider_runs, reverse=True)
    return rows[:20]
