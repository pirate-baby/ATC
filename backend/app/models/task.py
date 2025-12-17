from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import PlanTaskStatus

# Association table for task blocking relationships (DAG)
task_blocking = Table(
    "task_blocking",
    Base.metadata,
    Column(
        "task_id",
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "blocked_by_id",
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Task(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tasks"

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PlanTaskStatus] = mapped_column(
        Enum(PlanTaskStatus, name="plan_task_status", native_enum=True, create_type=False),
        default=PlanTaskStatus.BACKLOG,
        nullable=False,
    )
    branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    worktree_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Coding session fields (merged from CodingSession)
    session_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    session_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    session_output_log: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    plan: Mapped["Plan | None"] = relationship(
        "Plan", back_populates="tasks", foreign_keys=[plan_id]
    )
    child_plans: Mapped[list["Plan"]] = relationship(
        "Plan", back_populates="parent_task", foreign_keys="Plan.parent_task_id"
    )

    # DAG blocking relationship (many-to-many self-referential)
    blocked_by: Mapped[list["Task"]] = relationship(
        "Task",
        secondary=task_blocking,
        primaryjoin="Task.id == task_blocking.c.task_id",
        secondaryjoin="Task.id == task_blocking.c.blocked_by_id",
        backref="blocks",
    )

    comment_threads: Mapped[list["CommentThread"]] = relationship(
        "CommentThread",
        primaryjoin="and_(Task.id == foreign(CommentThread.target_id), "
        "CommentThread.target_type.in_(['task', 'line']))",
        viewonly=True,
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review",
        primaryjoin="and_(Task.id == foreign(Review.target_id), "
        "Review.target_type == 'task')",
        viewonly=True,
    )
