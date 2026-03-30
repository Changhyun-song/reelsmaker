import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    parent_type: Mapped[str] = mapped_column(String(50))
    parent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    asset_type: Mapped[str] = mapped_column(String(50))
    storage_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    provider_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_runs.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    status: Mapped[str] = mapped_column(String(50), server_default="pending")
    is_selected: Mapped[bool] = mapped_column(
        Boolean, server_default="false", default=False, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Variant management ──
    generation_batch: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True,
        comment="Groups assets from the same generation run",
    )
    quality_note: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="User memo on variant quality for comparison",
    )

    project: Mapped["Project"] = relationship(back_populates="assets")
    provider_run: Mapped["ProviderRun | None"] = relationship(
        foreign_keys=[provider_run_id],
    )
