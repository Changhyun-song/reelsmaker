import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), server_default="draft")
    active_style_preset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("style_presets.id", use_alter=True, name="fk_project_active_style"),
        nullable=True,
    )
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    active_style_preset: Mapped["StylePreset | None"] = relationship(
        foreign_keys=[active_style_preset_id], lazy="joined",
    )
    style_presets: Mapped[list["StylePreset"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
        foreign_keys="StylePreset.project_id",
    )
    script_versions: Mapped[list["ScriptVersion"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
        order_by="ScriptVersion.version.desc()",
    )
    character_profiles: Mapped[list["CharacterProfile"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
    )
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
    )
    timelines: Mapped[list["Timeline"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
    )
    provider_runs: Mapped[list["ProviderRun"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
    )
