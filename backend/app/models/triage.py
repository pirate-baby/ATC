import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin
from app.schemas.triage import TriageItemStatus


class TriageConnection(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "triage_connections"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Provider: linear, github_issues, jira, gitlab_issues
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    items: Mapped[list["TriageItem"]] = relationship(
        "TriageItem", back_populates="connection", lazy="selectin", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(  # noqa: F821
        "Project", back_populates="triage_connection", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<TriageConnection(id={self.id}, name={self.name}, provider={self.provider})>"


class TriageItem(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "triage_items"

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("triage_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    external_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default=TriageItemStatus.PENDING.value, nullable=False, index=True
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    connection: Mapped["TriageConnection"] = relationship(
        "TriageConnection", back_populates="items", lazy="selectin"
    )
    plan: Mapped["Plan | None"] = relationship(  # noqa: F821
        "Plan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<TriageItem(id={self.id}, title={self.title}, status={self.status})>"
