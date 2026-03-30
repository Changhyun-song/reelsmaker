"""Add input_params and plan_json to script_versions

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "script_versions",
        sa.Column("input_params", postgresql.JSON(), nullable=True),
    )
    op.add_column(
        "script_versions",
        sa.Column("plan_json", postgresql.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("script_versions", "plan_json")
    op.drop_column("script_versions", "input_params")
