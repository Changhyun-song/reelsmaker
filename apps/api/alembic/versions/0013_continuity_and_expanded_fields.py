"""Add continuity_profiles table + expand style_presets & character_profiles fields.

Revision ID: 0013
Revises: 0012
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── New table: continuity_profiles ──
    op.create_table(
        "continuity_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("color_palette_lock", sa.Text(), nullable=True),
        sa.Column("lighting_anchor", sa.Text(), nullable=True),
        sa.Column("color_temperature_range", sa.Text(), nullable=True),
        sa.Column("environment_consistency", sa.Text(), nullable=True),
        sa.Column("style_anchor_summary", sa.Text(), nullable=True),
        sa.Column("character_lock_notes", sa.Text(), nullable=True),
        sa.Column("forbidden_global_drift", sa.Text(), nullable=True),
        sa.Column("temporal_rules", sa.Text(), nullable=True),
        sa.Column("reference_asset_ids", postgresql.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── Expand style_presets ──
    op.add_column("style_presets", sa.Column("style_anchor", sa.Text(), nullable=True))
    op.add_column("style_presets", sa.Column("color_temperature", sa.String(200), nullable=True))
    op.add_column("style_presets", sa.Column("texture_quality", sa.String(200), nullable=True))
    op.add_column("style_presets", sa.Column("depth_style", sa.String(200), nullable=True))
    op.add_column("style_presets", sa.Column("environment_rules", sa.Text(), nullable=True))
    op.add_column("style_presets", sa.Column("reference_asset_ids", postgresql.JSON(), nullable=True))

    # ── Expand character_profiles ──
    op.add_column("character_profiles", sa.Column("body_type", sa.String(200), nullable=True))
    op.add_column("character_profiles", sa.Column("hair_description", sa.Text(), nullable=True))
    op.add_column("character_profiles", sa.Column("skin_tone", sa.String(200), nullable=True))
    op.add_column("character_profiles", sa.Column("signature_props", sa.Text(), nullable=True))
    op.add_column("character_profiles", sa.Column("forbidden_drift", sa.Text(), nullable=True))
    op.add_column("character_profiles", sa.Column("reference_asset_ids", postgresql.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("character_profiles", "reference_asset_ids")
    op.drop_column("character_profiles", "forbidden_drift")
    op.drop_column("character_profiles", "signature_props")
    op.drop_column("character_profiles", "skin_tone")
    op.drop_column("character_profiles", "hair_description")
    op.drop_column("character_profiles", "body_type")

    op.drop_column("style_presets", "reference_asset_ids")
    op.drop_column("style_presets", "environment_rules")
    op.drop_column("style_presets", "depth_style")
    op.drop_column("style_presets", "texture_quality")
    op.drop_column("style_presets", "color_temperature")
    op.drop_column("style_presets", "style_anchor")

    op.drop_table("continuity_profiles")
