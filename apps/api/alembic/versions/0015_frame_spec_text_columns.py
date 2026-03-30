"""Widen frame_spec varchar(200) columns to TEXT.

AI-generated frame descriptions routinely exceed 200 characters.
Affected columns: subject_position, camera_angle, lens_feel, mood.

Revision ID: 0015
Revises: 0014
"""

from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

_COLUMNS = ["subject_position", "camera_angle", "lens_feel", "mood"]


def upgrade() -> None:
    for col in _COLUMNS:
        op.alter_column(
            "frame_specs",
            col,
            type_=sa.Text(),
            existing_type=sa.String(200),
            existing_nullable=True,
        )


def downgrade() -> None:
    for col in _COLUMNS:
        op.alter_column(
            "frame_specs",
            col,
            type_=sa.String(200),
            existing_type=sa.Text(),
            existing_nullable=True,
        )
