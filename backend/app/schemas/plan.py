from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import PlanTaskStatus


class PlanBase(BaseModel):
    """Base plan fields."""

    title: str = Field(description="Plan title")
    content: str | None = Field(default=None, description="Markdown content describing the plan")


class PlanCreate(PlanBase):
    """Schema for creating a plan."""

    parent_task_id: UUID | None = Field(
        default=None, description="Task ID if this plan was spawned by a complex task"
    )


class PlanUpdate(BaseModel):
    """Schema for updating a plan."""

    title: str | None = Field(default=None, description="Plan title")
    content: str | None = Field(default=None, description="Markdown content")


class Plan(PlanBase):
    """Full plan response schema."""

    id: UUID = Field(description="Plan unique identifier")
    project_id: UUID = Field(description="Parent project ID")
    status: PlanTaskStatus = Field(description="Current plan status")
    parent_task_id: UUID | None = Field(
        default=None, description="Task ID if this plan was spawned by a complex task"
    )
    version: int = Field(default=1, description="Plan version number")
    created_by: UUID | None = Field(default=None, description="User or system that created")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")

    model_config = {"from_attributes": True}


class PlanWithDetails(Plan):
    """Plan with related entities."""

    tasks: list["TaskSummary"] = Field(default_factory=list, description="Tasks spawned by plan")
    reviews: list["ReviewSummary"] = Field(default_factory=list, description="Reviews on this plan")
    threads: list["ThreadSummary"] = Field(
        default_factory=list, description="Comment threads on this plan"
    )


class TaskSummary(BaseModel):
    """Summary of a task for embedding."""

    id: UUID
    title: str
    status: PlanTaskStatus


class ReviewSummary(BaseModel):
    """Summary of a review for embedding."""

    id: UUID
    reviewer_id: UUID
    decision: str
    created_at: datetime


class ThreadSummary(BaseModel):
    """Summary of a comment thread for embedding."""

    id: UUID
    status: str
    comment_count: int


PlanWithDetails.model_rebuild()
