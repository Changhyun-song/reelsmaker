"""Add rich fields to style_presets and character_profiles, seed global presets

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEED_PRESETS = [
    {
        "name": "Cinematic Realism",
        "description": "Film-grade photorealistic visuals with cinematic color grading and depth of field.",
        "style_keywords": "cinematic, photorealistic, film grain, anamorphic, color grading, 35mm film",
        "color_palette": "Rich warm tones, teal-orange contrast, deep shadows, golden highlights",
        "rendering_style": "Photorealistic CGI with filmic post-processing, subtle lens imperfections",
        "camera_language": "Shallow depth of field, anamorphic bokeh, lens flares, rack focus, steady dolly moves",
        "lighting_rules": "Three-point cinematic lighting, motivated practical lights, volumetric haze, golden hour preferred",
        "negative_rules": "cartoon, anime, flat shading, oversaturated, stock photo, watermark, text overlay",
        "prompt_prefix": "cinematic film still, photorealistic, 35mm anamorphic, shallow depth of field, film grain, color graded,",
        "negative_prompt": "cartoon, anime, illustration, painting, drawing, flat, 2D, low quality, blurry, watermark, text, logo, oversaturated, HDR",
    },
    {
        "name": "Premium Product Ad",
        "description": "Clean, high-end product advertisement style with studio lighting and minimal backgrounds.",
        "style_keywords": "commercial, product photography, studio lighting, clean, premium, luxury, minimalist",
        "color_palette": "Clean whites, soft grays, subtle accent colors, high contrast, controlled shadows",
        "rendering_style": "High-end product photography, 8K detail, controlled studio environment",
        "camera_language": "Sharp focus across product, macro details, smooth orbiting camera, static hero shots",
        "lighting_rules": "Softbox key light, gradient background, edge rim lighting, controlled reflections, no harsh shadows",
        "negative_rules": "messy background, natural lighting, handheld camera, motion blur, warm tones unless intentional",
        "prompt_prefix": "premium product advertisement, studio photography, softbox lighting, clean minimal background, 8K detail,",
        "negative_prompt": "cluttered, messy, natural lighting, handheld, blurry, low quality, watermark, text, cheap, low-end",
    },
    {
        "name": "Korean Webtoon",
        "description": "Modern Korean webtoon illustration style with clean lineart and soft cel-shading.",
        "style_keywords": "webtoon, manhwa, Korean illustration, cel-shading, clean lineart, soft coloring, digital art",
        "color_palette": "Soft pastels with vivid accents, clean gradients, white highlights, subtle warm undertones",
        "rendering_style": "Digital illustration, clean vector-like lineart, soft cel-shading, slight glow effects",
        "camera_language": "Flat composition with depth suggested by layering, dramatic angles for action, eye-level for dialogue",
        "lighting_rules": "Soft ambient light, dramatic rim lighting for emphasis, gradient sky backgrounds, glowing magical effects",
        "negative_rules": "photorealistic, 3D render, film grain, noise, sketch quality, rough lineart, Western comic style",
        "prompt_prefix": "Korean webtoon style illustration, manhwa, clean digital lineart, soft cel-shading, vivid colors,",
        "negative_prompt": "photorealistic, 3D render, photograph, film grain, noisy, sketch, rough, Western comic, Marvel, DC",
    },
    {
        "name": "Minimalist Infographic",
        "description": "Clean data-driven visual style with flat design, icons, and clear typography spaces.",
        "style_keywords": "infographic, flat design, minimalist, geometric, icon-based, data visualization, clean",
        "color_palette": "Limited palette (3-4 colors), bold primary colors, white space, high contrast text areas",
        "rendering_style": "Flat vector illustration, geometric shapes, isometric elements, no gradients or minimal",
        "camera_language": "Orthographic/flat view, no perspective distortion, centered compositions, grid-based layout",
        "lighting_rules": "No realistic lighting, flat even illumination, subtle drop shadows for depth hierarchy only",
        "negative_rules": "photorealistic, 3D, complex textures, gradients, lens effects, film grain, natural scenes",
        "prompt_prefix": "minimalist infographic illustration, flat design, geometric shapes, clean vector art, bold colors,",
        "negative_prompt": "photorealistic, 3D render, photograph, complex texture, gradient, lens flare, film grain, natural, organic",
    },
]


def upgrade() -> None:
    # StylePreset new columns
    op.add_column("style_presets", sa.Column("style_keywords", sa.Text(), nullable=True))
    op.add_column("style_presets", sa.Column("color_palette", sa.Text(), nullable=True))
    op.add_column("style_presets", sa.Column("rendering_style", sa.Text(), nullable=True))
    op.add_column("style_presets", sa.Column("camera_language", sa.Text(), nullable=True))
    op.add_column("style_presets", sa.Column("lighting_rules", sa.Text(), nullable=True))
    op.add_column("style_presets", sa.Column("negative_rules", sa.Text(), nullable=True))

    # CharacterProfile new columns
    op.add_column("character_profiles", sa.Column("role", sa.String(100), nullable=True))
    op.add_column("character_profiles", sa.Column("appearance", sa.Text(), nullable=True))
    op.add_column("character_profiles", sa.Column("outfit", sa.Text(), nullable=True))
    op.add_column("character_profiles", sa.Column("age_impression", sa.String(100), nullable=True))
    op.add_column("character_profiles", sa.Column("personality", sa.Text(), nullable=True))
    op.add_column("character_profiles", sa.Column("facial_traits", sa.Text(), nullable=True))
    op.add_column("character_profiles", sa.Column("pose_rules", sa.Text(), nullable=True))
    op.add_column("character_profiles", sa.Column("forbidden_changes", sa.Text(), nullable=True))
    op.add_column(
        "character_profiles",
        sa.Column(
            "reference_asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Seed global style presets
    style_presets = sa.table(
        "style_presets",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_global", sa.Boolean),
        sa.column("prompt_prefix", sa.Text),
        sa.column("negative_prompt", sa.Text),
        sa.column("style_keywords", sa.Text),
        sa.column("color_palette", sa.Text),
        sa.column("rendering_style", sa.Text),
        sa.column("camera_language", sa.Text),
        sa.column("lighting_rules", sa.Text),
        sa.column("negative_rules", sa.Text),
    )

    for preset in SEED_PRESETS:
        op.execute(
            style_presets.insert().values(
                id=sa.text("gen_random_uuid()"),
                name=preset["name"],
                description=preset["description"],
                is_global=True,
                prompt_prefix=preset["prompt_prefix"],
                negative_prompt=preset["negative_prompt"],
                style_keywords=preset["style_keywords"],
                color_palette=preset["color_palette"],
                rendering_style=preset["rendering_style"],
                camera_language=preset["camera_language"],
                lighting_rules=preset["lighting_rules"],
                negative_rules=preset["negative_rules"],
            )
        )


def downgrade() -> None:
    op.execute("DELETE FROM style_presets WHERE is_global = true")

    op.drop_column("character_profiles", "reference_asset_id")
    op.drop_column("character_profiles", "forbidden_changes")
    op.drop_column("character_profiles", "pose_rules")
    op.drop_column("character_profiles", "facial_traits")
    op.drop_column("character_profiles", "personality")
    op.drop_column("character_profiles", "age_impression")
    op.drop_column("character_profiles", "outfit")
    op.drop_column("character_profiles", "appearance")
    op.drop_column("character_profiles", "role")

    op.drop_column("style_presets", "negative_rules")
    op.drop_column("style_presets", "lighting_rules")
    op.drop_column("style_presets", "camera_language")
    op.drop_column("style_presets", "rendering_style")
    op.drop_column("style_presets", "color_palette")
    op.drop_column("style_presets", "style_keywords")
