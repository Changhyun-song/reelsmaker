import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class ScriptVersion(TimestampMixin, Base):
    __tablename__ = "script_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), server_default="draft")
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("script_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    input_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    plan_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="script_versions")
    parent_version: Mapped["ScriptVersion | None"] = relationship(
        remote_side="ScriptVersion.id", foreign_keys=[parent_version_id],
    )
    scenes: Mapped[list["Scene"]] = relationship(
        back_populates="script_version", cascade="all, delete-orphan",
        order_by="Scene.order_index",
    )
    subtitle_tracks: Mapped[list["SubtitleTrack"]] = relationship(
        back_populates="script_version", cascade="all, delete-orphan",
    )
