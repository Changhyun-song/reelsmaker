import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class CharacterProfile(TimestampMixin, Base):
    __tablename__ = "character_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_image_keys: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    voice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voice_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    style_attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    appearance: Mapped[str | None] = mapped_column(Text, nullable=True)
    outfit: Mapped[str | None] = mapped_column(Text, nullable=True)
    age_impression: Mapped[str | None] = mapped_column(String(100), nullable=True)
    personality: Mapped[str | None] = mapped_column(Text, nullable=True)
    facial_traits: Mapped[str | None] = mapped_column(Text, nullable=True)
    pose_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    forbidden_changes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Extended identity fields (continuity system) ──
    body_type: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="Build description e.g. 'slim athletic build, 170cm'",
    )
    hair_description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Detailed hair: color, length, style, texture",
    )
    skin_tone: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="Skin color/tone e.g. 'fair with warm undertones'",
    )
    signature_props: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Items always present: glasses, watch, necklace, etc.",
    )
    forbidden_drift: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Structured list of what MUST NOT change between shots",
    )
    reference_asset_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="Multiple reference image Asset UUIDs",
    )

    project: Mapped["Project"] = relationship(back_populates="character_profiles")
    reference_asset: Mapped["Asset | None"] = relationship(
        foreign_keys=[reference_asset_id],
    )
