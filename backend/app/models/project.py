import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProjectSettings(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "project_settings"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    required_approvals_plan: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    required_approvals_task: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    auto_approve_main_updates: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assigned_hats: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, nullable=False
    )

    # Relationship back to project
    project: Mapped["Project"] = relationship("Project", back_populates="settings")

    def __repr__(self) -> str:
        return f"<ProjectSettings(id={self.id}, project_id={self.project_id})>"


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    git_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    main_branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    triage_connection_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("triage_connections.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    settings: Mapped["ProjectSettings | None"] = relationship(
        "ProjectSettings",
        back_populates="project",
        uselist=False,
        lazy="joined",
        cascade="all, delete-orphan",
    )
    plans: Mapped[list["Plan"]] = relationship(  # noqa: F821
        "Plan", back_populates="project", lazy="selectin", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task", back_populates="project", lazy="selectin", cascade="all, delete-orphan"
    )
    triage_connection: Mapped["TriageConnection | None"] = relationship(  # noqa: F821
        "TriageConnection", back_populates="projects", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name})>"
