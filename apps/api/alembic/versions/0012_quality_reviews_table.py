"""Create quality_reviews table for manual/auto quality evaluations.

Revision ID: 0012
Revises: 0011
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quality_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_type", sa.String(30), server_default="project", nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(20), server_default="manual", nullable=False),
        sa.Column("scores", postgresql.JSON(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("reviewer", sa.String(30), server_default="human", nullable=False),
        sa.Column("run_label", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_quality_reviews_project_id", "quality_reviews", ["project_id"])
    op.create_index("ix_quality_reviews_target_id", "quality_reviews", ["target_id"])
    op.create_index("ix_quality_reviews_source", "quality_reviews", ["source"])


def downgrade() -> None:
    op.drop_table("quality_reviews")
