from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ProcessingStatus
from app.schemas.common import PlanTaskStatus


class PlanBase(BaseModel):
    title: str = Field(description="Plan title")
    content: str | None = Field(default=None, description="Markdown content describing the plan")


class PlanCreate(PlanBase):
    parent_task_id: UUID | None = Field(
        default=None, description="Task ID if this plan was spawned by a complex task"
    )


class PlanUpdate(BaseModel):
    title: str | None = Field(default=None, description="Plan title")
    content: str | None = Field(default=None, description="Markdown content")


class Plan(PlanBase):
    id: UUID = Field(description="Plan unique identifier")
    project_id: UUID = Field(description="Parent project ID")
    status: PlanTaskStatus = Field(description="Current plan status")
    parent_task_id: UUID | None = Field(
        default=None, description="Task ID if this plan was spawned by a complex task"
    )
    version: int = Field(default=1, description="Plan version number")
    processing_status: ProcessingStatus | None = Field(
        default=None, description="Status of AI content generation"
    )
    processing_error: str | None = Field(
        default=None, description="Error message if generation failed"
    )
    created_by: UUID | None = Field(default=None, description="User or system that created")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")

    model_config = {"from_attributes": True}


class PlanWithDetails(Plan):
    tasks: list["TaskSummary"] = Field(default_factory=list, description="Tasks spawned by plan")
    reviews: list["ReviewSummary"] = Field(default_factory=list, description="Reviews on this plan")
    threads: list["ThreadSummary"] = Field(
        default_factory=list, description="Comment threads on this plan"
    )


class TaskSummary(BaseModel):
    id: UUID
    title: str
    status: PlanTaskStatus


class ReviewSummary(BaseModel):
    id: UUID
    reviewer_id: UUID
    decision: str
    created_at: datetime


class ThreadSummary(BaseModel):
    id: UUID
    status: str
    comment_count: int


class PlanGenerateRequest(BaseModel):
    """Request to generate plan content using Claude."""

    context: str | None = Field(
        default=None,
        description="Additional context to provide to Claude for plan generation",
    )


class PlanGenerationStatus(BaseModel):
    """Response showing the current generation status of a plan."""

    plan_id: UUID = Field(description="Plan ID")
    processing_status: ProcessingStatus | None = Field(
        description="Current processing status"
    )
    processing_error: str | None = Field(
        default=None, description="Error message if generation failed"
    )
    content: str | None = Field(
        default=None, description="Generated content if completed"
    )


class SpawnTasksRequest(BaseModel):
    """Request to spawn tasks from an approved plan."""

    pass  # No additional parameters needed; plan content is used


class SpawnedTaskSummary(BaseModel):
    """Summary of a task spawned from a plan."""

    id: UUID = Field(description="Task ID")
    title: str = Field(description="Task title")
    description: str | None = Field(default=None, description="Task description")
    blocked_by: list[UUID] = Field(
        default_factory=list, description="IDs of tasks that block this task"
    )


class SpawnTasksResponse(BaseModel):
    """Response from spawning tasks from a plan."""

    plan_id: UUID = Field(description="Plan ID that spawned the tasks")
    tasks_created: int = Field(description="Number of tasks created")
    tasks: list[SpawnedTaskSummary] = Field(description="List of spawned tasks")


class SpawnTasksStatus(BaseModel):
    """Status response for task spawning progress."""

    plan_id: UUID = Field(description="Plan ID")
    processing_status: ProcessingStatus | None = Field(
        description="Current processing status"
    )
    processing_error: str | None = Field(
        default=None, description="Error message if spawning failed"
    )
    tasks_created: int | None = Field(
        default=None, description="Number of tasks created (if completed)"
    )


PlanWithDetails.model_rebuild()
