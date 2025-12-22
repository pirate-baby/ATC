from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    git_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    main_branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    triage_connection_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("triage_connections.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    settings: Mapped["ProjectSettings"] = relationship(
        "ProjectSettings", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    plans: Mapped[list["Plan"]] = relationship(
        "Plan", back_populates="project", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="project", cascade="all, delete-orphan"
    )
    triage_connection: Mapped["TriageConnection | None"] = relationship(
        "TriageConnection", back_populates="projects"
    )


class ProjectSettings(Base, UUIDMixin):
    __tablename__ = "project_settings"

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    required_approvals_plan: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    required_approvals_task: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    auto_approve_main_updates: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assigned_hats: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), default=list, nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="settings")
