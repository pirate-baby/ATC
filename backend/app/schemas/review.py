from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewDecision(str, Enum):
    APPROVED = "approved"
    REQUEST_CHANGES = "request_changes"
    COMMENT_ONLY = "comment_only"


class ReviewTargetType(str, Enum):
    PLAN = "plan"
    TASK = "task"


class ReviewCreate(BaseModel):
    decision: ReviewDecision = Field(description="Review decision")
    comment: str | None = Field(default=None, description="Review comment")


class Review(BaseModel):
    id: UUID = Field(description="Review unique identifier")
    target_type: ReviewTargetType = Field(description="Type of target entity")
    target_id: UUID = Field(description="ID of target entity")
    reviewer_id: UUID = Field(description="Reviewer user ID")
    decision: ReviewDecision = Field(description="Review decision")
    comment: str | None = Field(default=None, description="Review comment")
    created_at: datetime = Field(description="Creation timestamp")

    model_config = {"from_attributes": True}
