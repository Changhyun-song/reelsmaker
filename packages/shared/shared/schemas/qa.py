from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QAIssue(BaseModel):
    """Single QA issue produced by a rule check (before DB persistence)."""
    scope: str = Field(..., pattern=r"^(project|scene|shot|frame)$")
    target_type: str | None = None
    target_id: str | None = None
    check_type: str
    severity: str = Field(..., pattern=r"^(error|warning|info)$")
    message: str
    details: dict | None = None
    suggestion: str | None = None
    source: str = "rule"


class QAResultResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    script_version_id: UUID | None
    scope: str
    target_type: str | None
    target_id: UUID | None
    check_type: str
    severity: str
    message: str
    details: dict | None
    suggestion: str | None
    resolved: bool
    source: str
    created_at: datetime


class QAListResponse(BaseModel):
    results: list[QAResultResponse]
    total: int


class QASummary(BaseModel):
    total: int
    errors: int
    warnings: int
    infos: int
    by_check_type: dict[str, int]
    by_scope: dict[str, int]
    render_ready: bool
    blocking_issues: list[QAResultResponse]


class QARunRequest(BaseModel):
    script_version_id: str | None = None
    checks: list[str] | None = Field(
        None,
        description="Optional filter: only run these check types. None = all.",
    )


class QARunResponse(BaseModel):
    total_issues: int
    errors: int
    warnings: int
    infos: int
    render_ready: bool
