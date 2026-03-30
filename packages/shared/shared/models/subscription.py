"""User subscription and usage tracking for SaaS billing."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False,
    )
    tier: Mapped[str] = mapped_column(
        String(50), server_default="free", nullable=False,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True,
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True,
    )
    status: Mapped[str] = mapped_column(
        String(50), server_default="active", nullable=False,
    )

    # Usage limits per billing period
    max_projects: Mapped[int] = mapped_column(Integer, server_default="3")
    max_generations_per_month: Mapped[int] = mapped_column(Integer, server_default="50")
    generations_used: Mapped[int] = mapped_column(Integer, server_default="0")

    current_period_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False,
    )
