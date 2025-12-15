from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HATBase(BaseModel):
    name: str = Field(description="HAT name")
    description: str | None = Field(default=None, description="HAT description")
    definition: str | None = Field(
        default=None, description="The actual HAT content/definition"
    )
    enabled: bool = Field(default=True, description="Whether HAT is enabled")


class HATCreate(HATBase):
    pass


class HATUpdate(BaseModel):
    name: str | None = Field(default=None, description="HAT name")
    description: str | None = Field(default=None, description="HAT description")
    definition: str | None = Field(default=None, description="The HAT content/definition")
    enabled: bool | None = Field(default=None, description="Whether HAT is enabled")


class HAT(HATBase):
    id: UUID = Field(description="HAT unique identifier")
    created_at: datetime = Field(description="Creation timestamp")

    model_config = {"from_attributes": True}
