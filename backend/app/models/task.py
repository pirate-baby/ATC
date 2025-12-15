import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.common import PlanTaskStatus

# Self-referential many-to-many for task blocking relationships (DAG)
task_blocking = Table(
    "task_blocking",
    Base.metadata,
    Column(
        "blocked_task_id",
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "blocking_task_id",
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Task(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tasks"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=PlanTaskStatus.BACKLOG.value, nullable=False, index=True
    )
    branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    worktree_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship(  # noqa: F821
        "Project", back_populates="tasks", lazy="selectin"
    )
    plan: Mapped["Plan | None"] = relationship(  # noqa: F821
        "Plan", back_populates="tasks", foreign_keys=[plan_id], lazy="selectin"
    )

    # Self-referential many-to-many: blocked_by tasks that must complete before this task
    blocked_by: Mapped[list["Task"]] = relationship(
        "Task",
        secondary=task_blocking,
        primaryjoin="Task.id == task_blocking.c.blocked_task_id",
        secondaryjoin="Task.id == task_blocking.c.blocking_task_id",
        backref="blocks",
        lazy="selectin",
    )

    # Tasks can spawn sub-plans (for complex tasks)
    spawned_plans: Mapped[list["Plan"]] = relationship(  # noqa: F821
        "Plan",
        back_populates="parent_task",
        foreign_keys="[Plan.parent_task_id]",
        lazy="selectin",
    )

    reviews: Mapped[list["Review"]] = relationship(  # noqa: F821
        "Review",
        primaryjoin=(
            "and_(Task.id == foreign(Review.target_id), "
            "Review.target_type == 'task')"
        ),
        lazy="selectin",
        viewonly=True,
    )
    threads: Mapped[list["CommentThread"]] = relationship(  # noqa: F821
        "CommentThread",
        primaryjoin=(
            "and_(Task.id == foreign(CommentThread.target_id), "
            "CommentThread.target_type.in_(['task', 'code_line']))"
        ),
        lazy="selectin",
        viewonly=True,
    )
    coding_sessions: Mapped[list["CodingSession"]] = relationship(  # noqa: F821
        "CodingSession",
        primaryjoin=(
            "and_(Task.id == foreign(CodingSession.target_id), "
            "CodingSession.target_type == 'task')"
        ),
        lazy="selectin",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title}, status={self.status})>"
