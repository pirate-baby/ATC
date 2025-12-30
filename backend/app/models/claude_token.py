from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ClaudeTokenStatus


class ClaudeToken(Base, UUIDMixin, TimestampMixin):
    """Stores encrypted Claude subscription tokens for the shared pool."""

    __tablename__ = "claude_tokens"

    # One-to-one relationship with user
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Friendly name for the token (e.g., "Personal Account", "Work Subscription")
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Encrypted token value (never exposed in full)
    encrypted_token: Mapped[str] = mapped_column(Text, nullable=False)

    # Token status
    status: Mapped[ClaudeTokenStatus] = mapped_column(
        Enum(ClaudeTokenStatus, name="claude_token_status", native_enum=True, create_type=False),
        nullable=False,
        default=ClaudeTokenStatus.ACTIVE,
    )

    # Usage tracking
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Rate limit tracking (5-hour windows for Pro/Max)
    rate_limit_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Error tracking
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship to user
    user: Mapped["User"] = relationship("User", back_populates="claude_token")
