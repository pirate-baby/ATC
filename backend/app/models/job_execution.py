"""Job execution model for tracking background task history."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class JobStatus(str, Enum):
    """Status of a background job execution."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class JobExecution(Base, UUIDMixin, TimestampMixin):
    """Tracks execution history of background jobs."""

    __tablename__ = "job_executions"

    # Job identification
    job_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Related entity (e.g., plan_id for plan generation)
    target_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Status and execution info
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="job_status", native_enum=True, create_type=False),
        default=JobStatus.QUEUED,
        nullable=False,
        index=True,
    )

    # Retry tracking
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Timing
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Input/output
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metrics
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Worker info
    worker_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
