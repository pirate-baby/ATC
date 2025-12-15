from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class TargetType(str, Enum):
    """Type of entity a comment thread is attached to."""

    PLAN = "plan"
    TASK = "task"
    CODE_LINE = "code_line"


class CommentThreadStatus(str, Enum):
    """Status of a comment thread."""

    OPEN = "open"
    RESOLVED = "resolved"
    SUMMARIZED = "summarized"


class CommentBase(BaseModel):
    """Base comment fields."""

    content: str = Field(description="Comment content")
    parent_comment_id: UUID | None = Field(
        default=None, description="Parent comment ID for replies"
    )


class CommentCreate(CommentBase):
    """Schema for creating a comment."""

    pass


class Comment(CommentBase):
    """Full comment response schema."""

    id: UUID = Field(description="Comment unique identifier")
    thread_id: UUID = Field(description="Parent thread ID")
    author_id: UUID = Field(description="Author user ID")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")

    model_config = {"from_attributes": True}


class CommentThreadBase(BaseModel):
    """Base comment thread fields."""

    target_type: TargetType = Field(description="Type of target entity")
    file_path: str | None = Field(default=None, description="File path for code_line comments")
    line_number: int | None = Field(default=None, description="Line number for code_line comments")


class CommentThreadCreate(CommentThreadBase):
    """Schema for creating a comment thread."""

    initial_comment: str = Field(description="Initial comment content")


class CommentThread(CommentThreadBase):
    """Full comment thread response schema."""

    id: UUID = Field(description="Thread unique identifier")
    target_id: UUID = Field(description="ID of target entity")
    status: CommentThreadStatus = Field(
        default=CommentThreadStatus.OPEN, description="Thread status"
    )
    summary: str | None = Field(default=None, description="AI-generated summary of final decision")
    created_at: datetime = Field(description="Creation timestamp")

    model_config = {"from_attributes": True}


class CommentThreadWithComments(CommentThread):
    """Comment thread with all comments."""

    comments: list[Comment] = Field(default_factory=list, description="All comments in thread")
