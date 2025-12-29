from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def _validate_git_url_value(v: str) -> str:
    """Validate git URL - accepts local paths or URLs with valid schemes."""
    v = v.strip()
    if not v:
        raise ValueError("git_url cannot be empty")
    # If it starts with / or ~, treat as local path
    if v.startswith("/") or v.startswith("~"):
        return v
    # Otherwise validate as URL with allowed schemes
    allowed_schemes = ["http", "https", "file", "git", "ssh"]
    # Check if it looks like a URL (has scheme)
    if "://" in v:
        scheme = v.split("://")[0].lower()
        if scheme not in allowed_schemes:
            raise ValueError(f"URL scheme must be one of: {', '.join(allowed_schemes)}")
    # SSH shorthand format like git@github.com:user/repo.git
    elif "@" in v and ":" in v:
        return v
    else:
        raise ValueError(
            "git_url must be a local path (starting with / or ~), "
            "a URL with scheme (http, https, file, git, ssh), "
            "or SSH shorthand (git@host:path)"
        )
    return v


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

    model_config = {"from_attributes": True}


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
    git_url: str = Field(description="Git repository URL or local path")
    main_branch: str = Field(default="main", description="Primary branch name")

    @field_validator("git_url")
    @classmethod
    def validate_git_url(cls, v: str) -> str:
        return _validate_git_url_value(v)


class ProjectCreate(ProjectBase):
    settings: ProjectSettings | None = Field(
        default=None, description="Project settings (optional, defaults applied if not provided)"
    )
    triage_connection_id: UUID | None = Field(
        default=None, description="Associated triage connection ID"
    )


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, description="Human-readable project name")
    git_url: str | None = Field(default=None, description="Git repository URL or local path")
    main_branch: str | None = Field(default=None, description="Primary branch name")
    triage_connection_id: UUID | None = Field(
        default=None, description="Associated triage connection ID"
    )

    @field_validator("git_url")
    @classmethod
    def validate_git_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_git_url_value(v)


class Project(ProjectBase):
    id: UUID = Field(description="Project unique identifier")
    settings: ProjectSettings = Field(description="Project settings")
    triage_connection_id: UUID | None = Field(
        default=None, description="Associated triage connection ID"
    )
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")

    model_config = {"from_attributes": True}
