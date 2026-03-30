from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StylePresetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    style_keywords: str | None = None
    color_palette: str | None = None
    rendering_style: str | None = None
    camera_language: str | None = None
    lighting_rules: str | None = None
    negative_rules: str | None = None
    prompt_prefix: str | None = None
    prompt_suffix: str | None = None
    negative_prompt: str | None = None
    model_preferences: dict | None = None
    is_global: bool = False
    style_anchor: str | None = None
    color_temperature: str | None = None
    texture_quality: str | None = None
    depth_style: str | None = None
    environment_rules: str | None = None
    reference_asset_ids: list[str] | None = None


class StylePresetUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    style_keywords: str | None = None
    color_palette: str | None = None
    rendering_style: str | None = None
    camera_language: str | None = None
    lighting_rules: str | None = None
    negative_rules: str | None = None
    prompt_prefix: str | None = None
    prompt_suffix: str | None = None
    negative_prompt: str | None = None
    model_preferences: dict | None = None
    style_anchor: str | None = None
    color_temperature: str | None = None
    texture_quality: str | None = None
    depth_style: str | None = None
    environment_rules: str | None = None
    reference_asset_ids: list[str] | None = None


class StylePresetResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID | None
    name: str
    description: str | None
    style_keywords: str | None
    color_palette: str | None
    rendering_style: str | None
    camera_language: str | None
    lighting_rules: str | None
    negative_rules: str | None
    prompt_prefix: str | None
    prompt_suffix: str | None
    negative_prompt: str | None
    model_preferences: dict | None
    example_image_key: str | None
    is_global: bool
    style_anchor: str | None
    color_temperature: str | None
    texture_quality: str | None
    depth_style: str | None
    environment_rules: str | None
    reference_asset_ids: list[str] | None
    created_at: datetime
    updated_at: datetime


class StylePresetListResponse(BaseModel):
    presets: list[StylePresetResponse]
    total: int
