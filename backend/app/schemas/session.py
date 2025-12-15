from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class SessionTargetType(str, Enum):
    PLAN = "plan"
    TASK = "task"


class CodingSessionStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    ABORTED = "aborted"


class CodingSession(BaseModel):
    id: UUID = Field(description="Session unique identifier")
    target_type: SessionTargetType = Field(description="Type of target entity")
    target_id: UUID = Field(description="ID of target entity (plan or task)")
    status: CodingSessionStatus = Field(description="Session status")
    started_at: datetime = Field(description="Start timestamp")
    ended_at: datetime | None = Field(default=None, description="End timestamp if completed")
    output_log: str | None = Field(
        default=None, description="Full session output (stored after completion)"
    )

    model_config = {"from_attributes": True}
