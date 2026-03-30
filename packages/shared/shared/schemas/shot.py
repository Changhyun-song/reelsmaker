from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ShotResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    scene_id: UUID
    order_index: int
    shot_type: str | None
    description: str | None
    camera_movement: str | None
    duration_sec: float | None
    status: str
    purpose: str | None
    camera_framing: str | None
    subject: str | None
    environment: str | None
    emotion: str | None
    narration_segment: str | None
    transition_in: str | None
    transition_out: str | None
    asset_strategy: str | None
    plan_json: dict | None
    created_at: datetime
    updated_at: datetime


class ShotListResponse(BaseModel):
    shots: list[ShotResponse]
    total: int
    total_duration_sec: float
