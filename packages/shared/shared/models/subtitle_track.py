import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class SubtitleTrack(TimestampMixin, Base):
    __tablename__ = "subtitle_tracks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    script_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("script_versions.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )

    language: Mapped[str] = mapped_column(String(10), server_default="ko")
    format: Mapped[str] = mapped_column(String(10), server_default="srt")
    timing_source: Mapped[str] = mapped_column(
        String(30), server_default="estimated",
    )

    segments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    style_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_segments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(50), server_default="pending")

    script_version: Mapped["ScriptVersion | None"] = relationship(
        back_populates="subtitle_tracks",
        foreign_keys=[script_version_id],
    )
    asset: Mapped["Asset | None"] = relationship(foreign_keys=[asset_id])
