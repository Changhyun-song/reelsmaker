from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SceneResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    script_version_id: UUID
    order_index: int
    title: str | None
    description: str | None
    setting: str | None
    mood: str | None
    duration_estimate_sec: float | None
    status: str
    purpose: str | None
    narration_text: str | None
    emotional_tone: str | None
    visual_intent: str | None
    transition_hint: str | None
    plan_json: dict | None
    created_at: datetime
    updated_at: datetime


class SceneListResponse(BaseModel):
    scenes: list[SceneResponse]
    total: int
    total_duration_sec: float
