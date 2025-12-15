import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin
from app.schemas.comment import CommentThreadStatus


class CommentThread(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "comment_threads"

    # Target type: plan, task, code_line
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    file_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=CommentThreadStatus.OPEN.value, nullable=False, index=True
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="thread", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CommentThread(id={self.id}, status={self.status})>"


class Comment(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "comments"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comment_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comments.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    thread: Mapped["CommentThread"] = relationship(
        "CommentThread", back_populates="comments", lazy="selectin"
    )
    author: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="comments", lazy="selectin"
    )
    parent_comment: Mapped["Comment | None"] = relationship(
        "Comment", remote_side="Comment.id", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, thread_id={self.thread_id}, author_id={self.author_id})>"
