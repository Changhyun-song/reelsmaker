"""QualityReview — stores manual and auto quality evaluations.

Each review targets either a project or a specific entity (shot, scene, etc.)
and contains per-criterion 1-5 scores plus an optional comment.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class QualityReview(Base):
    __tablename__ = "quality_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )

    # "project" | "scene" | "shot"
    target_type: Mapped[str] = mapped_column(String(30), server_default="project")
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
    )

    # "manual" | "auto"
    source: Mapped[str] = mapped_column(String(20), server_default="manual", index=True)

    # Per-criterion scores: {"script_quality": 4, "scene_structure": 3, ...}
    scores: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # "human" | "system" | "claude"
    reviewer: Mapped[str] = mapped_column(String(30), server_default="human")

    # Optional: which run/version this evaluation refers to
    run_label: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
