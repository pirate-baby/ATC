from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ProjectSettings(BaseModel):
    required_approvals_plan: int = Field(
        default=1, ge=1, description="Number of approvals required for Plans"
    )
    required_approvals_task: int = Field(
        default=1, ge=1, description="Number of approvals required for Tasks"
    )
    auto_approve_main_updates: bool = Field(
        default=False, description="Auto-approve plans updated due to main branch changes"
    )
    assigned_hats: list[UUID] = Field(
        default_factory=list, description="HAT IDs assigned to this project"
    )


class ProjectSettingsUpdate(BaseModel):
    required_approvals_plan: int | None = Field(
        default=None, ge=1, description="Number of approvals required for Plans"
    )
    required_approvals_task: int | None = Field(
        default=None, ge=1, description="Number of approvals required for Tasks"
    )
    auto_approve_main_updates: bool | None = Field(
        default=None, description="Auto-approve plans updated due to main branch changes"
    )
    assigned_hats: list[UUID] | None = Field(
        default=None, description="HAT IDs assigned to this project"
    )


class ProjectBase(BaseModel):
    name: str = Field(description="Human-readable project name")
    git_url: HttpUrl = Field(description="Git repository URL")
    main_branch: str = Field(default="main", description="Primary branch name")


class ProjectCreate(ProjectBase):
    settings: ProjectSettings | None = Field(
        default=None, description="Project settings (optional, defaults applied if not provided)"
    )
    triage_connection_id: UUID | None = Field(
        default=None, description="Associated triage connection ID"
    )


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, description="Human-readable project name")
    git_url: HttpUrl | None = Field(default=None, description="Git repository URL")
    main_branch: str | None = Field(default=None, description="Primary branch name")
    triage_connection_id: UUID | None = Field(
        default=None, description="Associated triage connection ID"
    )


class Project(ProjectBase):
    id: UUID = Field(description="Project unique identifier")
    settings: ProjectSettings = Field(description="Project settings")
    triage_connection_id: UUID | None = Field(
        default=None, description="Associated triage connection ID"
    )
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")

    model_config = {"from_attributes": True}
