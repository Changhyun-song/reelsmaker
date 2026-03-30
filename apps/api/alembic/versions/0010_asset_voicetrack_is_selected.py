"""Add is_selected to assets and voice_tracks for variant selection.

Revision ID: 0010
Revises: 0009
"""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assets",
        sa.Column(
            "is_selected",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.create_index("ix_assets_is_selected", "assets", ["is_selected"])

    op.add_column(
        "voice_tracks",
        sa.Column(
            "is_selected",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.create_index("ix_voice_tracks_is_selected", "voice_tracks", ["is_selected"])


def downgrade() -> None:
    op.drop_index("ix_voice_tracks_is_selected", table_name="voice_tracks")
    op.drop_column("voice_tracks", "is_selected")
    op.drop_index("ix_assets_is_selected", table_name="assets")
    op.drop_column("assets", "is_selected")
