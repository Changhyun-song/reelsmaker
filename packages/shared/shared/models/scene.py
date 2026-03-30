import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class Scene(TimestampMixin, Base):
    __tablename__ = "scenes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    script_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("script_versions.id", ondelete="CASCADE"),
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    setting: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mood: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_estimate_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), server_default="drafted")

    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    narration_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    emotional_tone: Mapped[str | None] = mapped_column(String(200), nullable=True)
    visual_intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    transition_hint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    plan_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    script_version: Mapped["ScriptVersion"] = relationship(back_populates="scenes")
    shots: Mapped[list["Shot"]] = relationship(
        back_populates="scene", cascade="all, delete-orphan",
        order_by="Shot.order_index",
    )
