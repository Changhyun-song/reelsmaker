"""Add rich shot planning fields to shots table

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("shots", sa.Column("purpose", sa.Text(), nullable=True))
    op.add_column("shots", sa.Column("camera_framing", sa.String(100), nullable=True))
    op.add_column("shots", sa.Column("subject", sa.Text(), nullable=True))
    op.add_column("shots", sa.Column("environment", sa.Text(), nullable=True))
    op.add_column("shots", sa.Column("emotion", sa.String(200), nullable=True))
    op.add_column("shots", sa.Column("narration_segment", sa.Text(), nullable=True))
    op.add_column("shots", sa.Column("transition_in", sa.String(200), nullable=True))
    op.add_column("shots", sa.Column("transition_out", sa.String(200), nullable=True))
    op.add_column("shots", sa.Column("asset_strategy", sa.String(50), nullable=True))
    op.add_column("shots", sa.Column("plan_json", postgresql.JSON(), nullable=True))

    op.execute("UPDATE shots SET status = 'drafted' WHERE status = 'draft'")
    op.execute("UPDATE shots SET status = 'drafted' WHERE status = 'ready'")


def downgrade() -> None:
    op.execute("UPDATE shots SET status = 'draft' WHERE status = 'drafted'")

    op.drop_column("shots", "plan_json")
    op.drop_column("shots", "asset_strategy")
    op.drop_column("shots", "transition_out")
    op.drop_column("shots", "transition_in")
    op.drop_column("shots", "narration_segment")
    op.drop_column("shots", "emotion")
    op.drop_column("shots", "environment")
    op.drop_column("shots", "subject")
    op.drop_column("shots", "camera_framing")
    op.drop_column("shots", "purpose")
