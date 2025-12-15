import uuid
from datetime import datetime
from typing import Self

from fastapi import HTTPException
from sqlalchemy import DateTime, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    @classmethod
    def get_or_404(cls, session: Session, id: uuid.UUID, detail: str | None = None) -> Self:
        obj = session.scalar(select(cls).where(cls.id == id))  # type: ignore[attr-defined]
        if not obj:
            raise HTTPException(status_code=404, detail=detail or f"{cls.__name__} not found")
        return obj


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
