import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class FrameSpec(TimestampMixin, Base):
    __tablename__ = "frame_specs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shots.id", ondelete="CASCADE"), index=True
    )
    order_index: Mapped[int] = mapped_column(Integer)
    visual_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    character_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    dialogue: Mapped[str | None] = mapped_column(Text, nullable=True)
    dialogue_character_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("character_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    duration_ms: Mapped[int] = mapped_column(Integer, server_default="3000")
    transition_type: Mapped[str] = mapped_column(String(50), server_default="cut")
    status: Mapped[str] = mapped_column(String(50), server_default="drafted")

    frame_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    composition: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject_position: Mapped[str | None] = mapped_column(Text, nullable=True)
    camera_angle: Mapped[str | None] = mapped_column(Text, nullable=True)
    lens_feel: Mapped[str | None] = mapped_column(Text, nullable=True)
    lighting: Mapped[str | None] = mapped_column(Text, nullable=True)
    mood: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_pose: Mapped[str | None] = mapped_column(Text, nullable=True)
    background_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    continuity_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    forbidden_elements: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    shot: Mapped["Shot"] = relationship(back_populates="frame_specs")
    dialogue_character: Mapped["CharacterProfile | None"] = relationship(
        foreign_keys=[dialogue_character_id],
    )
    voice_track: Mapped["VoiceTrack | None"] = relationship(
        back_populates="frame_spec", uselist=False,
    )
