from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class HATType(str, Enum):
    """Type of HAT implementation."""

    SLASH_COMMAND = "slash_command"
    SKILL = "skill"
    SUBAGENT = "subagent"


class HATBase(BaseModel):
    """Base HAT fields."""

    name: str = Field(description="HAT name")
    type: HATType = Field(description="HAT type (slash_command, skill, subagent)")
    description: str | None = Field(default=None, description="HAT description")
    definition: str | None = Field(
        default=None, description="The actual command/skill/agent content"
    )
    enabled: bool = Field(default=True, description="Whether HAT is enabled")


class HATCreate(HATBase):
    """Schema for creating a HAT."""

    pass


class HATUpdate(BaseModel):
    """Schema for updating a HAT."""

    name: str | None = Field(default=None, description="HAT name")
    type: HATType | None = Field(default=None, description="HAT type")
    description: str | None = Field(default=None, description="HAT description")
    definition: str | None = Field(default=None, description="The command/skill/agent content")
    enabled: bool | None = Field(default=None, description="Whether HAT is enabled")


class HAT(HATBase):
    """Full HAT response schema."""

    id: UUID = Field(description="HAT unique identifier")
    created_at: datetime = Field(description="Creation timestamp")

    model_config = {"from_attributes": True}
