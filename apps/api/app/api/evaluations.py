"""Quality Evaluation API — manual scoring, auto evaluation, history."""

from __future__ import annotations

import uuid as _uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.quality_review import QualityReview
from shared.qa.criteria import (
    compute_weighted_average,
    criteria_for_scope,
)
from shared.qa.evaluator import run_auto_evaluation_with_summary
from shared.schemas.evaluation import (
    AutoEvalRequest,
    CriterionInfo,
    EvaluationCreate,
    EvaluationListResponse,
    EvaluationResponse,
    EvaluationSummary,
)

router = APIRouter()


# ── Criteria metadata ────────────────────────────────

@router.get("/{project_id}/evaluations/criteria", response_model=list[CriterionInfo])
async def list_criteria(
    project_id: UUID,
    scope: str = Query("project", pattern=r"^(project|scene|shot)$"),
):
    """Return evaluation criteria applicable to the given scope."""
    return [
        CriterionInfo(
            key=c.key,
            label=c.label,
            description=c.description,
            scopes=list(c.scopes),
            weight=c.weight,
        )
        for c in criteria_for_scope(scope)
    ]


# ── Manual evaluation ────────────────────────────────

@router.post("/{project_id}/evaluations", response_model=EvaluationResponse)
async def create_evaluation(
    project_id: UUID,
    body: EvaluationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Submit a manual quality evaluation."""
    valid_keys = {c.key for c in criteria_for_scope(body.target_type)}
    invalid = set(body.scores.keys()) - valid_keys
    if invalid:
        raise HTTPException(400, f"Invalid criteria for scope '{body.target_type}': {invalid}")

    for key, val in body.scores.items():
        if not (1 <= val <= 5):
            raise HTTPException(400, f"Score for '{key}' must be 1-5, got {val}")

    overall = compute_weighted_average(body.scores)

    review = QualityReview(
        project_id=project_id,
        target_type=body.target_type,
        target_id=_uuid.UUID(body.target_id) if body.target_id else None,
        source="manual",
        scores=body.scores,
        overall_score=overall,
        comment=body.comment,
        reviewer="human",
        run_label=body.run_label,
    )
    db.add(review)
    await db.flush()
    await db.refresh(review)

    return review


# ── Auto evaluation ──────────────────────────────────

@router.post("/{project_id}/evaluations/auto", response_model=EvaluationResponse)
async def run_auto_evaluation(
    project_id: UUID,
    body: AutoEvalRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Run automatic quality evaluation and persist the result."""
    from app.api.qa import _build_context

    req = body or AutoEvalRequest()
    svid: UUID | None = UUID(req.script_version_id) if req.script_version_id else None

    ctx = await _build_context(db, project_id, svid)
    scores, overall = run_auto_evaluation_with_summary(ctx)

    review = QualityReview(
        project_id=project_id,
        target_type="project",
        target_id=None,
        source="auto",
        scores=scores,
        overall_score=overall,
        comment=None,
        reviewer="system",
        run_label=req.run_label,
    )
    db.add(review)
    await db.flush()
    await db.refresh(review)

    return review


# ── List / History ───────────────────────────────────

@router.get("/{project_id}/evaluations", response_model=EvaluationListResponse)
async def list_evaluations(
    project_id: UUID,
    source: str | None = Query(None, pattern=r"^(manual|auto)$"),
    target_type: str | None = Query(None, pattern=r"^(project|scene|shot)$"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List quality evaluations for a project."""
    q = select(QualityReview).where(QualityReview.project_id == project_id)

    if source:
        q = q.where(QualityReview.source == source)
    if target_type:
        q = q.where(QualityReview.target_type == target_type)

    q = q.order_by(QualityReview.created_at.desc()).limit(limit)

    result = await db.execute(q)
    items = list(result.scalars().all())

    return EvaluationListResponse(reviews=items, total=len(items))


# ── Summary ──────────────────────────────────────────

@router.get("/{project_id}/evaluations/summary", response_model=EvaluationSummary)
async def evaluation_summary(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Aggregated evaluation summary."""
    result = await db.execute(
        select(QualityReview)
        .where(QualityReview.project_id == project_id)
        .order_by(QualityReview.created_at.desc())
    )
    all_reviews = list(result.scalars().all())

    manual = [r for r in all_reviews if r.source == "manual"]
    auto = [r for r in all_reviews if r.source == "auto"]

    latest_auto = auto[0] if auto else None
    latest_manual = manual[0] if manual else None

    history = [
        {
            "id": str(r.id),
            "source": r.source,
            "overall_score": r.overall_score,
            "reviewer": r.reviewer,
            "run_label": r.run_label,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in all_reviews[:20]
    ]

    return EvaluationSummary(
        total_reviews=len(all_reviews),
        manual_count=len(manual),
        auto_count=len(auto),
        latest_auto_score=latest_auto.overall_score if latest_auto else None,
        latest_manual_score=latest_manual.overall_score if latest_manual else None,
        latest_auto_scores=latest_auto.scores if latest_auto else None,
        latest_manual_scores=latest_manual.scores if latest_manual else None,
        score_history=history,
    )


# ── Detail / Delete ──────────────────────────────────

@router.get("/{project_id}/evaluations/{review_id}", response_model=EvaluationResponse)
async def get_evaluation(
    project_id: UUID,
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    review = (
        await db.execute(select(QualityReview).where(QualityReview.id == review_id))
    ).scalar_one_or_none()
    if not review or review.project_id != project_id:
        raise HTTPException(404, "Evaluation not found")
    return review


@router.delete("/{project_id}/evaluations/{review_id}")
async def delete_evaluation(
    project_id: UUID,
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    review = (
        await db.execute(select(QualityReview).where(QualityReview.id == review_id))
    ).scalar_one_or_none()
    if not review or review.project_id != project_id:
        raise HTTPException(404, "Evaluation not found")
    await db.delete(review)
    await db.flush()
    return {"deleted": str(review_id)}
