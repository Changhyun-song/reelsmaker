"""Add rich frame planning fields to frame_specs table

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("frame_specs", sa.Column("frame_role", sa.String(20), nullable=True))
    op.add_column("frame_specs", sa.Column("composition", sa.Text(), nullable=True))
    op.add_column("frame_specs", sa.Column("subject_position", sa.String(200), nullable=True))
    op.add_column("frame_specs", sa.Column("camera_angle", sa.String(200), nullable=True))
    op.add_column("frame_specs", sa.Column("lens_feel", sa.String(200), nullable=True))
    op.add_column("frame_specs", sa.Column("lighting", sa.Text(), nullable=True))
    op.add_column("frame_specs", sa.Column("mood", sa.String(200), nullable=True))
    op.add_column("frame_specs", sa.Column("action_pose", sa.Text(), nullable=True))
    op.add_column("frame_specs", sa.Column("background_description", sa.Text(), nullable=True))
    op.add_column("frame_specs", sa.Column("continuity_notes", sa.Text(), nullable=True))
    op.add_column("frame_specs", sa.Column("forbidden_elements", sa.Text(), nullable=True))
    op.add_column("frame_specs", sa.Column("plan_json", postgresql.JSON(), nullable=True))

    op.execute("UPDATE frame_specs SET status = 'drafted' WHERE status = 'draft'")


def downgrade() -> None:
    op.execute("UPDATE frame_specs SET status = 'draft' WHERE status = 'drafted'")

    op.drop_column("frame_specs", "plan_json")
    op.drop_column("frame_specs", "forbidden_elements")
    op.drop_column("frame_specs", "continuity_notes")
    op.drop_column("frame_specs", "background_description")
    op.drop_column("frame_specs", "action_pose")
    op.drop_column("frame_specs", "mood")
    op.drop_column("frame_specs", "lighting")
    op.drop_column("frame_specs", "lens_feel")
    op.drop_column("frame_specs", "camera_angle")
    op.drop_column("frame_specs", "subject_position")
    op.drop_column("frame_specs", "composition")
    op.drop_column("frame_specs", "frame_role")
