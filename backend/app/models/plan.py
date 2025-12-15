import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.common import PlanTaskStatus


class Plan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "plans"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=PlanTaskStatus.BACKLOG.value, nullable=False, index=True
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship(  # noqa: F821
        "Project", back_populates="plans", lazy="selectin"
    )
    parent_task: Mapped["Task | None"] = relationship(  # noqa: F821
        "Task",
        back_populates="spawned_plans",
        foreign_keys=[parent_task_id],
        lazy="selectin",
    )
    creator: Mapped["User | None"] = relationship(  # noqa: F821
        "User", back_populates="created_plans", lazy="selectin"
    )
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task", back_populates="plan", foreign_keys="[Task.plan_id]", lazy="selectin"
    )
    reviews: Mapped[list["Review"]] = relationship(  # noqa: F821
        "Review",
        primaryjoin=(
            "and_(Plan.id == foreign(Review.target_id), "
            "Review.target_type == 'plan')"
        ),
        lazy="selectin",
        viewonly=True,
    )
    threads: Mapped[list["CommentThread"]] = relationship(  # noqa: F821
        "CommentThread",
        primaryjoin=(
            "and_(Plan.id == foreign(CommentThread.target_id), "
            "CommentThread.target_type == 'plan')"
        ),
        lazy="selectin",
        viewonly=True,
    )
    coding_sessions: Mapped[list["CodingSession"]] = relationship(  # noqa: F821
        "CodingSession",
        primaryjoin=(
            "and_(Plan.id == foreign(CodingSession.target_id), "
            "CodingSession.target_type == 'plan')"
        ),
        lazy="selectin",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<Plan(id={self.id}, title={self.title}, status={self.status})>"
