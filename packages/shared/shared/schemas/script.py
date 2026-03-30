from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ScriptPlanRequest(BaseModel):
    """Input for script plan generation."""

    topic: str = Field(..., min_length=1, max_length=500)
    target_audience: str = ""
    tone: str = ""
    duration_sec: int = Field(default=60, ge=10, le=600)
    format: str = "youtube_short"
    language: str = "ko"
    constraints: str = ""


class ScriptVersionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    version: int
    status: str
    raw_text: str | None
    input_params: dict | None
    plan_json: dict | None
    parent_version_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ScriptVersionListResponse(BaseModel):
    versions: list[ScriptVersionResponse]
    total: int
