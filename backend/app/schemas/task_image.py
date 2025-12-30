from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TaskImageBase(BaseModel):
    """Base schema for task images."""

    filename: str = Field(description="Stored filename (UUID-based)")
    original_filename: str = Field(description="Original uploaded filename")
    content_type: str = Field(description="MIME type of the image")
    size_bytes: int = Field(description="File size in bytes")


class TaskImage(TaskImageBase):
    """Response schema for a task image."""

    id: UUID = Field(description="Unique identifier")
    task_id: UUID = Field(description="Parent task ID")
    created_at: datetime = Field(description="Upload timestamp")

    model_config = {"from_attributes": True}


class TaskImageSummary(BaseModel):
    """Summary of a task image for inclusion in task responses."""

    id: UUID
    original_filename: str
    content_type: str
    size_bytes: int

    model_config = {"from_attributes": True}
