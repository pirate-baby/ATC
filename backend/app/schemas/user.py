from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class UserBase(BaseModel):
    """Base user fields."""

    git_handle: str = Field(description="GitHub/GitLab username")
    email: EmailStr = Field(description="User email address")
    display_name: str | None = Field(default=None, description="Display name")
    avatar_url: HttpUrl | None = Field(default=None, description="Avatar URL")


class UserCreate(UserBase):
    """Schema for creating a user."""

    pass


class User(UserBase):
    """Full user response schema."""

    id: UUID = Field(description="User unique identifier")
    created_at: datetime = Field(description="Creation timestamp")

    model_config = {"from_attributes": True}
