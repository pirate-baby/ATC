from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import PlanTaskStatus


class FileStatus(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class DiffLineType(str, Enum):
    ADD = "add"
    DELETE = "delete"
    CONTEXT = "context"


class DiffLine(BaseModel):
    type: DiffLineType = Field(description="Line type: add, delete, or context")
    content: str = Field(description="Line content (without +/- prefix)")
    old_line_number: int | None = Field(
        default=None, description="Line number in old file (None for additions)"
    )
    new_line_number: int | None = Field(
        default=None, description="Line number in new file (None for deletions)"
    )


class FileDiff(BaseModel):
    path: str = Field(description="File path")
    status: FileStatus = Field(description="File status (added/modified/deleted/renamed)")
    additions: int = Field(description="Number of lines added")
    deletions: int = Field(description="Number of lines deleted")
    patch: str = Field(description="Unified diff format patch")
    lines: list[DiffLine] | None = Field(
        default=None, description="Parsed diff lines with line numbers (for line-level views)"
    )


class CodeDiff(BaseModel):
    base_branch: str = Field(description="Base branch name")
    head_branch: str = Field(description="Head branch name (task branch)")
    files: list[FileDiff] = Field(description="List of file diffs")
    total_additions: int = Field(default=0, description="Total lines added across all files")
    total_deletions: int = Field(default=0, description="Total lines deleted across all files")


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

    @model_validator(mode="before")
    @classmethod
    def convert_model_fields(cls, data: Any) -> Any:
        """Convert ORM model fields to schema-compatible format."""
        if hasattr(data, "__table__"):
            # Convert blocked_by relationship to list of UUIDs
            blocked_by_ids = [t.id for t in data.blocked_by] if data.blocked_by else []
            # Convert status enum
            status_value = data.status.value if hasattr(data.status, "value") else data.status
            return {
                "id": data.id,
                "project_id": data.project_id,
                "plan_id": data.plan_id,
                "title": data.title,
                "description": data.description,
                "status": status_value,
                "blocked_by": blocked_by_ids,
                "branch_name": data.branch_name,
                "worktree_path": data.worktree_path,
                "version": data.version,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
            }
        return data


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


class StartSessionResponse(BaseModel):
    task_id: UUID = Field(description="Task ID")
    branch_name: str = Field(description="Git branch name created for this task")
    worktree_path: str = Field(description="Path to the git worktree")
    status: PlanTaskStatus = Field(description="New task status (should be 'coding')")
    session_started_at: datetime = Field(description="Timestamp when session started")


TaskWithDetails.model_rebuild()
