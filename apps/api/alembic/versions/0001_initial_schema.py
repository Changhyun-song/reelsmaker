"""Initial schema – all core tables

Revision ID: 0001
Revises:
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. projects (without active_style_preset_id to break circular dep)
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("settings", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 2. style_presets
    op.create_table(
        "style_presets",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("prompt_prefix", sa.Text(), nullable=True),
        sa.Column("prompt_suffix", sa.Text(), nullable=True),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("model_preferences", postgresql.JSON(), nullable=True),
        sa.Column("example_image_key", sa.String(500), nullable=True),
        sa.Column("is_global", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_style_presets_project_id", "style_presets", ["project_id"])

    # 3. Close the circular FK: add active_style_preset_id to projects
    op.add_column("projects", sa.Column("active_style_preset_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_project_active_style", "projects", "style_presets", ["active_style_preset_id"], ["id"], ondelete="SET NULL")

    # 4. script_versions
    op.create_table(
        "script_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("parent_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("script_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_script_versions_project_id", "script_versions", ["project_id"])

    # 5. character_profiles
    op.create_table(
        "character_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("visual_prompt", sa.Text(), nullable=True),
        sa.Column("reference_image_keys", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("voice_id", sa.String(255), nullable=True),
        sa.Column("voice_settings", postgresql.JSON(), nullable=True),
        sa.Column("style_attributes", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_character_profiles_project_id", "character_profiles", ["project_id"])

    # 6. scenes
    op.create_table(
        "scenes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("script_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("script_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("setting", sa.String(500), nullable=True),
        sa.Column("mood", sa.String(100), nullable=True),
        sa.Column("duration_estimate_sec", sa.Float(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scenes_script_version_id", "scenes", ["script_version_id"])

    # 7. shots
    op.create_table(
        "shots",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("shot_type", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("camera_movement", sa.String(100), nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_shots_scene_id", "shots", ["scene_id"])

    # 8. frame_specs
    op.create_table(
        "frame_specs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("shot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("visual_prompt", sa.Text(), nullable=True),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("character_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("dialogue", sa.Text(), nullable=True),
        sa.Column("dialogue_character_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("character_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("duration_ms", sa.Integer(), server_default="3000", nullable=False),
        sa.Column("transition_type", sa.String(50), server_default="cut", nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_frame_specs_shot_id", "frame_specs", ["shot_id"])

    # 9. provider_runs
    op.create_table(
        "provider_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("input_params", postgresql.JSON(), nullable=True),
        sa.Column("output_summary", postgresql.JSON(), nullable=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="started"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_usage", postgresql.JSON(), nullable=True),
        sa.Column("cost_estimate", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_provider_runs_project_id", "provider_runs", ["project_id"])

    # 10. assets
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_type", sa.String(50), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("storage_key", sa.String(1000), nullable=True),
        sa.Column("filename", sa.String(500), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("provider_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("provider_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_assets_project_id", "assets", ["project_id"])
    op.create_index("ix_assets_parent", "assets", ["parent_type", "parent_id"])
    op.create_index("ix_assets_provider_run_id", "assets", ["provider_run_id"])

    # Close deferred FK: provider_runs.asset_id → assets.id
    op.create_foreign_key("fk_provider_runs_asset", "provider_runs", "assets", ["asset_id"], ["id"], ondelete="SET NULL")

    # 11. voice_tracks
    op.create_table(
        "voice_tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("frame_spec_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("frame_specs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("character_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("character_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("voice_id", sa.String(255), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("timestamps", postgresql.JSON(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_voice_tracks_project_id", "voice_tracks", ["project_id"])
    op.create_index("ix_voice_tracks_frame_spec_id", "voice_tracks", ["frame_spec_id"])

    # 12. subtitle_tracks
    op.create_table(
        "subtitle_tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("script_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("script_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(10), nullable=False, server_default="srt"),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_subtitle_tracks_project_id", "subtitle_tracks", ["project_id"])
    op.create_index("ix_subtitle_tracks_script_version_id", "subtitle_tracks", ["script_version_id"])

    # 13. timelines
    op.create_table(
        "timelines",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("script_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("script_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_duration_ms", sa.Integer(), nullable=True),
        sa.Column("segments", postgresql.JSON(), nullable=True),
        sa.Column("bgm_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("subtitle_track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subtitle_tracks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_timelines_project_id", "timelines", ["project_id"])

    # 14. render_jobs
    op.create_table(
        "render_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("timelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("output_settings", postgresql.JSON(), nullable=True),
        sa.Column("output_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ffmpeg_command", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_render_jobs_project_id", "render_jobs", ["project_id"])
    op.create_index("ix_render_jobs_status", "render_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("render_jobs")
    op.drop_table("timelines")
    op.drop_table("subtitle_tracks")
    op.drop_table("voice_tracks")
    op.drop_constraint("fk_provider_runs_asset", "provider_runs", type_="foreignkey")
    op.drop_table("assets")
    op.drop_table("provider_runs")
    op.drop_table("frame_specs")
    op.drop_table("shots")
    op.drop_table("scenes")
    op.drop_table("character_profiles")
    op.drop_table("script_versions")
    op.drop_constraint("fk_project_active_style", "projects", type_="foreignkey")
    op.drop_column("projects", "active_style_preset_id")
    op.drop_table("style_presets")
    op.drop_table("projects")
