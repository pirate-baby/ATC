from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDMixin
from app.models.enums import TriageItemStatus, TriageProvider


class TriageConnection(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "triage_connections"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[TriageProvider] = mapped_column(
        Enum(TriageProvider, name="triage_provider", native_enum=True), nullable=False
    )
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    items: Mapped[list["TriageItem"]] = relationship(
        "TriageItem", back_populates="connection", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="triage_connection")


class TriageItem(Base, UUIDMixin):
    __tablename__ = "triage_items"

    connection_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("triage_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    external_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[TriageItemStatus] = mapped_column(
        Enum(TriageItemStatus, name="triage_item_status", native_enum=True),
        default=TriageItemStatus.PENDING,
        nullable=False,
    )
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    connection: Mapped["TriageConnection"] = relationship(
        "TriageConnection", back_populates="items"
    )
    plan: Mapped["Plan | None"] = relationship("Plan", back_populates="triage_item")
