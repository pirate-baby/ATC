from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import PlanTaskStatus


class FileStatus(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class FileDiff(BaseModel):
    path: str = Field(description="File path")
    status: FileStatus = Field(description="File status (added/modified/deleted/renamed)")
    additions: int = Field(description="Number of lines added")
    deletions: int = Field(description="Number of lines deleted")
    patch: str = Field(description="Unified diff format patch")


class CodeDiff(BaseModel):
    base_branch: str = Field(description="Base branch name")
    head_branch: str = Field(description="Head branch name (task branch)")
    files: list[FileDiff] = Field(description="List of file diffs")


class TaskBase(BaseModel):
    title: str = Field(description="Task title")
    description: str | None = Field(default=None, description="What needs to be done and why")


class TaskCreate(TaskBase):
    plan_id: UUID | None = Field(default=None, description="Parent plan that spawned this task")
    blocked_by: list[UUID] = Field(
        default_factory=list, description="Task IDs that must complete first (DAG)"
    )


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, description="Task title")
    description: str | None = Field(default=None, description="What needs to be done and why")


class BlockingTasksUpdate(BaseModel):
    blocked_by: list[UUID] = Field(
        description="Task IDs that must complete before this task can start"
    )


class Task(TaskBase):
    id: UUID = Field(description="Task unique identifier")
    project_id: UUID = Field(description="Parent project ID")
    plan_id: UUID | None = Field(default=None, description="Parent plan that spawned this task")
    status: PlanTaskStatus = Field(description="Current task status")
    blocked_by: list[UUID] = Field(
        default_factory=list, description="Task IDs that must complete first"
    )
    branch_name: str | None = Field(
        default=None, description="Git branch name (created when task enters Coding)"
    )
    worktree_path: str | None = Field(
        default=None, description="Git worktree path (created when task enters Coding)"
    )
    version: int = Field(default=1, description="Task version number")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")

    model_config = {"from_attributes": True}


class TaskWithDetails(Task):
    plan: "PlanSummary | None" = Field(default=None, description="Parent plan summary")
    blocking_tasks: list["TaskSummary"] = Field(
        default_factory=list, description="Tasks that block this task"
    )
    reviews: list["ReviewSummary"] = Field(default_factory=list, description="Reviews on this task")
    threads: list["ThreadSummary"] = Field(
        default_factory=list, description="Comment threads on this task"
    )
    active_session: "SessionSummary | None" = Field(
        default=None, description="Currently active coding session"
    )


class PlanSummary(BaseModel):
    id: UUID
    title: str
    status: PlanTaskStatus


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


class SessionSummary(BaseModel):
    id: UUID
    status: str
    started_at: datetime


TaskWithDetails.model_rebuild()
