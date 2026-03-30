import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class VoiceTrack(TimestampMixin, Base):
    __tablename__ = "voice_tracks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )

    shot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shots.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    frame_spec_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frame_specs.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    character_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("character_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    text: Mapped[str] = mapped_column(Text)
    voice_id: Mapped[str] = mapped_column(String(255))
    speaker_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), server_default="ko")
    speed: Mapped[float] = mapped_column(Float, server_default="1.0")
    emotion: Mapped[str | None] = mapped_column(String(100), nullable=True)

    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamps: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tts_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), server_default="pending")
    is_selected: Mapped[bool] = mapped_column(
        Boolean, server_default="false", default=False, index=True,
    )

    frame_spec: Mapped["FrameSpec | None"] = relationship(
        back_populates="voice_track",
        foreign_keys=[frame_spec_id],
    )
    shot: Mapped["Shot | None"] = relationship(foreign_keys=[shot_id])
    character_profile: Mapped["CharacterProfile | None"] = relationship(
        foreign_keys=[character_profile_id],
    )
    asset: Mapped["Asset | None"] = relationship(foreign_keys=[asset_id])
    provider_run: Mapped["ProviderRun | None"] = relationship(
        foreign_keys=[provider_run_id],
    )
