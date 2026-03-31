"""Add prompt_history table for prompt versioning.

Revision ID: 0018
Revises: 0017
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("frame_id", UUID(as_uuid=True), sa.ForeignKey("frame_specs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version", sa.Integer, server_default="1", nullable=False),
        sa.Column("prompt_text", sa.Text, nullable=False),
        sa.Column("negative_prompt", sa.Text, nullable=True),
        sa.Column("prompt_source", sa.String(50), server_default="compiler", nullable=False),
        sa.Column("quality_mode", sa.String(20), nullable=True),
        sa.Column("generation_batch", sa.String(100), nullable=True, index=True),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("is_current", sa.Boolean, server_default="false", nullable=False),
        sa.Column("metadata", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("prompt_history")
