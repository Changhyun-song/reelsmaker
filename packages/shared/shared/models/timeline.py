import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class Timeline(TimestampMixin, Base):
    __tablename__ = "timelines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    script_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("script_versions.id", ondelete="CASCADE"),
        index=True,
    )
    total_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    segments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    bgm_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    subtitle_track_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subtitle_tracks.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(50), server_default="draft")

    project: Mapped["Project"] = relationship(back_populates="timelines")
    render_jobs: Mapped[list["RenderJob"]] = relationship(
        back_populates="timeline", cascade="all, delete-orphan",
    )
    bgm_asset: Mapped["Asset | None"] = relationship(foreign_keys=[bgm_asset_id])
    subtitle_track: Mapped["SubtitleTrack | None"] = relationship(
        foreign_keys=[subtitle_track_id],
    )
