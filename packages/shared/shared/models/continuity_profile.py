import uuid

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class ContinuityProfile(TimestampMixin, Base):
    """Project-level continuity rules that enforce visual/stylistic consistency
    across all generated shots, frames, and assets."""

    __tablename__ = "continuity_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        unique=True, index=True,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean, server_default="true", default=True,
    )

    # ── Color & Lighting Anchors ──
    color_palette_lock: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Locked color palette: primary, secondary, accent colors with hex or descriptive values",
    )
    lighting_anchor: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Baseline lighting direction and style that must persist across all shots",
    )
    color_temperature_range: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Allowed color temp range e.g. '3000K-4500K warm dominant'",
    )

    # ── Environment & Style ──
    environment_consistency: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Environment rules: recurring props, textures, architectural style",
    )
    style_anchor_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Compiled one-paragraph style DNA from active StylePreset",
    )

    # ── Character Lock ──
    character_lock_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Which character attributes are absolutely locked across all shots",
    )

    # ── Drift Prevention ──
    forbidden_global_drift: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Things that must NEVER change in this project: style shifts, tone breaks, etc.",
    )
    temporal_rules: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="How visual elements evolve over time (or remain constant)",
    )

    # ── Reference Assets ──
    reference_asset_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="Project-level reference image Asset UUIDs for overall visual tone",
    )

    project: Mapped["Project"] = relationship(
        foreign_keys=[project_id],
    )
