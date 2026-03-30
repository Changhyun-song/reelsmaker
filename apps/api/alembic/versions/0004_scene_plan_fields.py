"""Add rich scene planning fields to scenes table

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scenes", sa.Column("purpose", sa.Text(), nullable=True))
    op.add_column("scenes", sa.Column("narration_text", sa.Text(), nullable=True))
    op.add_column("scenes", sa.Column("emotional_tone", sa.String(200), nullable=True))
    op.add_column("scenes", sa.Column("visual_intent", sa.Text(), nullable=True))
    op.add_column("scenes", sa.Column("transition_hint", sa.String(500), nullable=True))
    op.add_column("scenes", sa.Column("plan_json", postgresql.JSON(), nullable=True))

    op.execute("UPDATE scenes SET status = 'drafted' WHERE status = 'draft'")
    op.execute("UPDATE scenes SET status = 'drafted' WHERE status = 'ready'")


def downgrade() -> None:
    op.execute("UPDATE scenes SET status = 'draft' WHERE status = 'drafted'")

    op.drop_column("scenes", "plan_json")
    op.drop_column("scenes", "transition_hint")
    op.drop_column("scenes", "visual_intent")
    op.drop_column("scenes", "emotional_tone")
    op.drop_column("scenes", "narration_text")
    op.drop_column("scenes", "purpose")
