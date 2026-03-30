"""Add user_subscriptions table for SaaS billing.

Revision ID: 0017
Revises: 0016
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("tier", sa.String(50), server_default="free", nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True, unique=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True, unique=True),
        sa.Column("status", sa.String(50), server_default="active", nullable=False),
        sa.Column("max_projects", sa.Integer(), server_default="3"),
        sa.Column("max_generations_per_month", sa.Integer(), server_default="50"),
        sa.Column("generations_used", sa.Integer(), server_default="0"),
        sa.Column("current_period_start", sa.DateTime(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("metadata", JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_subscriptions")
