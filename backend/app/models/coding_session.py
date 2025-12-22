import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin
from app.schemas.session import CodingSessionStatus


class CodingSession(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "coding_sessions"

    target_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # plan, task
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50), default=CodingSessionStatus.RUNNING.value, nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    output_log: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<CodingSession(id={self.id}, status={self.status})>"
