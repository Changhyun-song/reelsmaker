"""Extend voice_tracks for shot-level TTS and metadata

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make frame_spec_id nullable
    op.alter_column(
        "voice_tracks", "frame_spec_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # Add shot_id column
    op.add_column(
        "voice_tracks",
        sa.Column("shot_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_voice_tracks_shot_id", "voice_tracks", ["shot_id"])
    op.create_foreign_key(
        "fk_voice_tracks_shot_id", "voice_tracks", "shots",
        ["shot_id"], ["id"], ondelete="CASCADE",
    )

    # Add TTS metadata fields
    op.add_column("voice_tracks", sa.Column("speaker_name", sa.String(255), nullable=True))
    op.add_column("voice_tracks", sa.Column("language", sa.String(10), server_default="ko"))
    op.add_column("voice_tracks", sa.Column("speed", sa.Float(), server_default="1.0"))
    op.add_column("voice_tracks", sa.Column("emotion", sa.String(100), nullable=True))
    op.add_column("voice_tracks", sa.Column("provider_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("voice_tracks", sa.Column("tts_metadata", postgresql.JSON(), nullable=True))

    op.create_foreign_key(
        "fk_voice_tracks_provider_run_id", "voice_tracks", "provider_runs",
        ["provider_run_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_voice_tracks_provider_run_id", "voice_tracks", type_="foreignkey")
    op.drop_column("voice_tracks", "tts_metadata")
    op.drop_column("voice_tracks", "provider_run_id")
    op.drop_column("voice_tracks", "emotion")
    op.drop_column("voice_tracks", "speed")
    op.drop_column("voice_tracks", "language")
    op.drop_column("voice_tracks", "speaker_name")

    op.drop_constraint("fk_voice_tracks_shot_id", "voice_tracks", type_="foreignkey")
    op.drop_index("ix_voice_tracks_shot_id", table_name="voice_tracks")
    op.drop_column("voice_tracks", "shot_id")

    op.alter_column(
        "voice_tracks", "frame_spec_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
