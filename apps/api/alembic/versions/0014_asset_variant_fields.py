"""Add generation_batch and quality_note to assets for multi-variant workflow.

Revision ID: 0014
Revises: 0013
"""

from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("generation_batch", sa.String(100), nullable=True))
    op.add_column("assets", sa.Column("quality_note", sa.Text(), nullable=True))
    op.create_index("ix_assets_generation_batch", "assets", ["generation_batch"])


def downgrade() -> None:
    op.drop_index("ix_assets_generation_batch", "assets")
    op.drop_column("assets", "quality_note")
    op.drop_column("assets", "generation_batch")
