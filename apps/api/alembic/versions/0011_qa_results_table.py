"""Create qa_results table for QA/Critic layer.

Revision ID: 0011
Revises: 0010
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "qa_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("script_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope", sa.String(30), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("check_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSON(), nullable=True),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("resolved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("source", sa.String(30), server_default="rule", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_qa_results_project_id", "qa_results", ["project_id"])
    op.create_index("ix_qa_results_script_version_id", "qa_results", ["script_version_id"])
    op.create_index("ix_qa_results_scope", "qa_results", ["scope"])
    op.create_index("ix_qa_results_target_id", "qa_results", ["target_id"])
    op.create_index("ix_qa_results_check_type", "qa_results", ["check_type"])
    op.create_index("ix_qa_results_severity", "qa_results", ["severity"])


def downgrade() -> None:
    op.drop_table("qa_results")
