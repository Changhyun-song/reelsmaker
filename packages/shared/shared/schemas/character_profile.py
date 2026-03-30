from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CharacterProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    role: str | None = None
    appearance: str | None = None
    outfit: str | None = None
    age_impression: str | None = None
    personality: str | None = None
    facial_traits: str | None = None
    pose_rules: str | None = None
    forbidden_changes: str | None = None
    visual_prompt: str | None = None
    voice_id: str | None = None
    voice_settings: dict | None = None
    reference_asset_id: UUID | None = None
    body_type: str | None = None
    hair_description: str | None = None
    skin_tone: str | None = None
    signature_props: str | None = None
    forbidden_drift: str | None = None
    reference_asset_ids: list[str] | None = None


class CharacterProfileUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    role: str | None = None
    appearance: str | None = None
    outfit: str | None = None
    age_impression: str | None = None
    personality: str | None = None
    facial_traits: str | None = None
    pose_rules: str | None = None
    forbidden_changes: str | None = None
    visual_prompt: str | None = None
    voice_id: str | None = None
    voice_settings: dict | None = None
    reference_asset_id: UUID | None = None
    body_type: str | None = None
    hair_description: str | None = None
    skin_tone: str | None = None
    signature_props: str | None = None
    forbidden_drift: str | None = None
    reference_asset_ids: list[str] | None = None


class CharacterProfileResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    name: str
    description: str | None
    role: str | None
    appearance: str | None
    outfit: str | None
    age_impression: str | None
    personality: str | None
    facial_traits: str | None
    pose_rules: str | None
    forbidden_changes: str | None
    visual_prompt: str | None
    reference_image_keys: list[str] | None
    voice_id: str | None
    voice_settings: dict | None
    style_attributes: dict | None
    reference_asset_id: UUID | None
    body_type: str | None
    hair_description: str | None
    skin_tone: str | None
    signature_props: str | None
    forbidden_drift: str | None
    reference_asset_ids: list[str] | None
    created_at: datetime
    updated_at: datetime


class CharacterProfileListResponse(BaseModel):
    characters: list[CharacterProfileResponse]
    total: int
