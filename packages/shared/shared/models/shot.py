import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class Shot(TimestampMixin, Base):
    __tablename__ = "shots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scene_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="CASCADE"), index=True
    )
    order_index: Mapped[int] = mapped_column(Integer)
    shot_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    camera_movement: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), server_default="drafted")

    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    camera_framing: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment: Mapped[str | None] = mapped_column(Text, nullable=True)
    emotion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    narration_segment: Mapped[str | None] = mapped_column(Text, nullable=True)
    transition_in: Mapped[str | None] = mapped_column(String(200), nullable=True)
    transition_out: Mapped[str | None] = mapped_column(String(200), nullable=True)
    asset_strategy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    plan_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    scene: Mapped["Scene"] = relationship(back_populates="shots")
    frame_specs: Mapped[list["FrameSpec"]] = relationship(
        back_populates="shot", cascade="all, delete-orphan",
        order_by="FrameSpec.order_index",
    )
