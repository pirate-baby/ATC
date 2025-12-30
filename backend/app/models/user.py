from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.claude_token import ClaudeToken


class User(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "users"

    git_handle: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Relationships
    plans_created: Mapped[list["Plan"]] = relationship(
        "Plan", back_populates="creator", foreign_keys="Plan.created_by"
    )
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="author")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="reviewer")
    claude_token: Mapped["ClaudeToken | None"] = relationship(
        "ClaudeToken", back_populates="user", uselist=False
    )
