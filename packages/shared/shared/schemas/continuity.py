from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ContinuityProfileUpdate(BaseModel):
    enabled: bool | None = None
    color_palette_lock: str | None = None
    lighting_anchor: str | None = None
    color_temperature_range: str | None = None
    environment_consistency: str | None = None
    style_anchor_summary: str | None = None
    character_lock_notes: str | None = None
    forbidden_global_drift: str | None = None
    temporal_rules: str | None = None
    reference_asset_ids: list[str] | None = None


class ContinuityProfileResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    enabled: bool
    color_palette_lock: str | None
    lighting_anchor: str | None
    color_temperature_range: str | None
    environment_consistency: str | None
    style_anchor_summary: str | None
    character_lock_notes: str | None
    forbidden_global_drift: str | None
    temporal_rules: str | None
    reference_asset_ids: list[str] | None
    created_at: datetime
    updated_at: datetime


class ContinuityContextResponse(BaseModel):
    """Compiled continuity context for preview — what gets injected into prompts."""

    style_anchor: str
    character_anchors: list[str]
    color_rules: str
    lighting_rules: str
    environment_rules: str
    forbidden_drift: list[str]
    reference_count: int
