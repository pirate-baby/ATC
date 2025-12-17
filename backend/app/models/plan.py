from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import PlanTaskStatus


class Plan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "plans"

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PlanTaskStatus] = mapped_column(
        Enum(PlanTaskStatus, name="plan_task_status", native_enum=True),
        default=PlanTaskStatus.BACKLOG,
        nullable=False,
    )
    parent_task_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="plans")
    parent_task: Mapped["Task | None"] = relationship(
        "Task", back_populates="child_plans", foreign_keys=[parent_task_id]
    )
    creator: Mapped["User | None"] = relationship("User", back_populates="plans_created")
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="plan", foreign_keys="Task.plan_id"
    )
    comment_threads: Mapped[list["CommentThread"]] = relationship(
        "CommentThread",
        primaryjoin="and_(Plan.id == foreign(CommentThread.target_id), "
        "CommentThread.target_type == 'plan')",
        viewonly=True,
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review",
        primaryjoin="and_(Plan.id == foreign(Review.target_id), "
        "Review.target_type == 'plan')",
        viewonly=True,
    )
    triage_item: Mapped["TriageItem | None"] = relationship(
        "TriageItem", back_populates="plan", uselist=False
    )
