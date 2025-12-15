from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class TriageProvider(str, Enum):
    """External issue tracker provider."""

    LINEAR = "linear"
    GITHUB_ISSUES = "github_issues"
    JIRA = "jira"
    GITLAB_ISSUES = "gitlab_issues"


class TriageItemStatus(str, Enum):
    """Status of an imported triage item."""

    PENDING = "pending"
    PLANNED = "planned"
    REJECTED = "rejected"


class TriageConnectionBase(BaseModel):
    """Base triage connection fields."""

    name: str = Field(description="Connection name")
    provider: TriageProvider = Field(description="Issue tracker provider")
    config: dict | None = Field(default=None, description="Provider-specific configuration")


class TriageConnectionCreate(TriageConnectionBase):
    """Schema for creating a triage connection."""

    pass


class TriageConnectionUpdate(BaseModel):
    """Schema for updating a triage connection."""

    name: str | None = Field(default=None, description="Connection name")
    config: dict | None = Field(default=None, description="Provider-specific configuration")


class TriageConnection(TriageConnectionBase):
    """Full triage connection response schema."""

    id: UUID = Field(description="Connection unique identifier")
    last_sync_at: datetime | None = Field(default=None, description="Last sync timestamp")
    created_at: datetime = Field(description="Creation timestamp")

    model_config = {"from_attributes": True}


class TriageItem(BaseModel):
    """An issue or ticket imported from a triage connection."""

    id: UUID = Field(description="Item unique identifier")
    connection_id: UUID = Field(description="Parent connection ID")
    external_id: str = Field(description="ID in external system")
    title: str = Field(description="Issue title")
    external_url: HttpUrl | None = Field(default=None, description="URL in external system")
    description: str | None = Field(default=None, description="Issue description")
    plan_id: UUID | None = Field(default=None, description="Plan ID if planned")
    status: TriageItemStatus = Field(default=TriageItemStatus.PENDING, description="Item status")
    imported_at: datetime = Field(description="Import timestamp")

    model_config = {"from_attributes": True}


class TriageItemPlan(BaseModel):
    """Schema for creating a plan from a triage item."""

    project_id: UUID = Field(description="Project to create the plan in")


class TriageItemReject(BaseModel):
    """Schema for rejecting a triage item."""

    reason: str | None = Field(default=None, description="Rejection reason")
