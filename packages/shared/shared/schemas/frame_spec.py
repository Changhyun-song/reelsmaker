from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FrameSpecResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    shot_id: UUID
    order_index: int
    frame_role: str | None
    composition: str | None
    subject_position: str | None
    camera_angle: str | None
    lens_feel: str | None
    lighting: str | None
    mood: str | None
    action_pose: str | None
    background_description: str | None
    continuity_notes: str | None
    forbidden_elements: str | None
    visual_prompt: str | None
    negative_prompt: str | None
    duration_ms: int
    transition_type: str
    status: str
    plan_json: dict | None
    created_at: datetime
    updated_at: datetime


class FrameSpecListResponse(BaseModel):
    frames: list[FrameSpecResponse]
    total: int
