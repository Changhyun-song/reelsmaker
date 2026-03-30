"""Pydantic schemas for quality evaluation API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CriterionInfo(BaseModel):
    key: str
    label: str
    description: str
    scopes: list[str]
    weight: float


class EvaluationCreate(BaseModel):
    """Manual evaluation submission."""
    target_type: str = Field("project", pattern=r"^(project|scene|shot)$")
    target_id: str | None = None
    scores: dict[str, int] = Field(
        ...,
        description="Per-criterion scores (1-5). Keys must match CRITERIA_KEYS.",
    )
    comment: str | None = None
    run_label: str | None = None


class EvaluationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    target_type: str
    target_id: UUID | None
    source: str
    scores: dict
    overall_score: float | None
    comment: str | None
    reviewer: str
    run_label: str | None
    created_at: datetime
    updated_at: datetime


class EvaluationListResponse(BaseModel):
    reviews: list[EvaluationResponse]
    total: int


class EvaluationSummary(BaseModel):
    """Aggregated evaluation summary for a project."""
    total_reviews: int
    manual_count: int
    auto_count: int
    latest_auto_score: float | None
    latest_manual_score: float | None
    latest_auto_scores: dict[str, int] | None
    latest_manual_scores: dict[str, int] | None
    score_history: list[dict]


class AutoEvalRequest(BaseModel):
    """Request body for auto evaluation."""
    script_version_id: str | None = None
    run_label: str | None = None
