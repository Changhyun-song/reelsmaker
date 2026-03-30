"""Expand subtitle_tracks: segments, timing_source, style_settings, language

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make script_version_id nullable
    op.alter_column(
        "subtitle_tracks", "script_version_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    op.add_column("subtitle_tracks", sa.Column("language", sa.String(10), server_default="ko"))
    op.add_column("subtitle_tracks", sa.Column(
        "timing_source", sa.String(30), server_default="estimated",
    ))
    op.add_column("subtitle_tracks", sa.Column("segments", postgresql.JSON(), nullable=True))
    op.add_column("subtitle_tracks", sa.Column("style_settings", postgresql.JSON(), nullable=True))
    op.add_column("subtitle_tracks", sa.Column("total_segments", sa.Integer(), nullable=True))
    op.add_column("subtitle_tracks", sa.Column("total_duration_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("subtitle_tracks", "total_duration_ms")
    op.drop_column("subtitle_tracks", "total_segments")
    op.drop_column("subtitle_tracks", "style_settings")
    op.drop_column("subtitle_tracks", "segments")
    op.drop_column("subtitle_tracks", "timing_source")
    op.drop_column("subtitle_tracks", "language")

    op.alter_column(
        "subtitle_tracks", "script_version_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
