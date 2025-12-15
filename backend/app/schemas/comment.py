from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class TargetType(str, Enum):
    PLAN = "plan"
    TASK = "task"
    CODE_LINE = "code_line"


class CommentThreadStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    SUMMARIZED = "summarized"


class CommentBase(BaseModel):
    content: str = Field(description="Comment content")
    parent_comment_id: UUID | None = Field(
        default=None, description="Parent comment ID for replies"
    )


class CommentCreate(CommentBase):
    pass


class Comment(CommentBase):
    id: UUID = Field(description="Comment unique identifier")
    thread_id: UUID = Field(description="Parent thread ID")
    author_id: UUID = Field(description="Author user ID")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")

    model_config = {"from_attributes": True}


class CommentThreadBase(BaseModel):
    target_type: TargetType = Field(description="Type of target entity")
    file_path: str | None = Field(default=None, description="File path for code_line comments")
    line_number: int | None = Field(default=None, description="Line number for code_line comments")


class CommentThreadCreate(CommentThreadBase):
    initial_comment: str = Field(description="Initial comment content")


class CommentThread(CommentThreadBase):
    id: UUID = Field(description="Thread unique identifier")
    target_id: UUID = Field(description="ID of target entity")
    status: CommentThreadStatus = Field(
        default=CommentThreadStatus.OPEN, description="Thread status"
    )
    summary: str | None = Field(default=None, description="AI-generated summary of final decision")
    created_at: datetime = Field(description="Creation timestamp")

    model_config = {"from_attributes": True}


class CommentThreadWithComments(CommentThread):
    comments: list[Comment] = Field(default_factory=list, description="All comments in thread")
