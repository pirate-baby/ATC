from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDMixin
from app.models.enums import CommentThreadStatus, CommentThreadTargetType


class CommentThread(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "comment_threads"

    target_type: Mapped[CommentThreadTargetType] = mapped_column(
        Enum(CommentThreadTargetType, name="comment_thread_target_type", native_enum=True),
        nullable=False,
    )
    target_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[CommentThreadStatus] = mapped_column(
        Enum(CommentThreadStatus, name="comment_thread_status", native_enum=True, create_type=False),
        default=CommentThreadStatus.OPEN,
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="thread", cascade="all, delete-orphan"
    )


class Comment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "comments"

    thread_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("comment_threads.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_comment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("comments.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    thread: Mapped["CommentThread"] = relationship("CommentThread", back_populates="comments")
    author: Mapped["User"] = relationship("User", back_populates="comments")
    parent_comment: Mapped["Comment | None"] = relationship(
        "Comment", remote_side="Comment.id", backref="replies"
    )
