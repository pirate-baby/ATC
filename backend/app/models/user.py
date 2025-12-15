from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    git_handle: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Remove updated_at from TimestampMixin since User schema doesn't have it
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = None  # type: ignore[assignment]

    # Relationships
    reviews: Mapped[list["Review"]] = relationship(  # noqa: F821
        "Review", back_populates="reviewer", lazy="selectin"
    )
    comments: Mapped[list["Comment"]] = relationship(  # noqa: F821
        "Comment", back_populates="author", lazy="selectin"
    )
    created_plans: Mapped[list["Plan"]] = relationship(  # noqa: F821
        "Plan", back_populates="creator", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, git_handle={self.git_handle})>"
