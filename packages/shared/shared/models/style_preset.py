import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class StylePreset(TimestampMixin, Base):
    __tablename__ = "style_presets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_prefix: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_suffix: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    example_image_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_global: Mapped[bool] = mapped_column(Boolean, server_default="false")

    style_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    color_palette: Mapped[str | None] = mapped_column(Text, nullable=True)
    rendering_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    camera_language: Mapped[str | None] = mapped_column(Text, nullable=True)
    lighting_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_rules: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Anchor fields (continuity system) ──
    style_anchor: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Core immutable style DNA: the one-sentence essence that must never change",
    )
    color_temperature: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="Dominant color temp e.g. 'warm 3200K' or 'cool 5500K'",
    )
    texture_quality: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="Surface quality e.g. 'photorealistic 8k' or 'painterly brushstrokes'",
    )
    depth_style: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="DOF preference e.g. 'shallow DOF f/1.4 isolating subject'",
    )
    environment_rules: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Rules for environment consistency across shots",
    )
    reference_asset_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="List of Asset UUIDs that visually define this style",
    )

    project: Mapped["Project | None"] = relationship(
        back_populates="style_presets", foreign_keys=[project_id],
    )
