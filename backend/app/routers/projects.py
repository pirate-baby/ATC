import subprocess
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from app.models.project import Project as ProjectModel
from app.models.project import ProjectSettings as ProjectSettingsModel
from app.schemas import (
    PaginatedResponse,
    Project,
    ProjectCreate,
    ProjectSettings,
    ProjectSettingsUpdate,
    ProjectUpdate,
    StandardError,
)

router = APIRouter()


def _validate_git_url(git_url: str) -> None:
    """Validate that a git URL is accessible.

    For local paths, checks if the directory exists and is a git repository.
    For remote URLs, uses git ls-remote to check accessibility.
    """
    parsed = urlparse(git_url)

    # Check if it's a local path (no scheme or file:// scheme)
    if not parsed.scheme or parsed.scheme == "file":
        local_path = parsed.path if parsed.scheme == "file" else git_url
        path = Path(local_path)

        if not path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Local repository path does not exist: {local_path}"
            )

        git_dir = path / ".git"
        if not git_dir.exists() and not (path.suffix == ".git" or path.name.endswith(".git")):
            raise HTTPException(
                status_code=400,
                detail=f"Path is not a git repository: {local_path}"
            )
        return

    # For remote URLs, use git ls-remote
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--exit-code", git_url],
            capture_output=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot access git repository: {git_url}"
            )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=400,
            detail=f"Timeout accessing git repository: {git_url}"
        )
    except FileNotFoundError:
        # git command not found - skip validation
        pass


def _create_project_settings(
    db: Session, project_id: UUID, settings_data: ProjectSettings | None
) -> ProjectSettingsModel:
    """Create ProjectSettings for a project."""
    if settings_data:
        settings_model = ProjectSettingsModel(
            project_id=project_id,
            required_approvals_plan=settings_data.required_approvals_plan,
            required_approvals_task=settings_data.required_approvals_task,
            auto_approve_main_updates=settings_data.auto_approve_main_updates,
            assigned_hats=settings_data.assigned_hats,
        )
    else:
        settings_model = ProjectSettingsModel(project_id=project_id)

    db.add(settings_model)
    return settings_model


@router.get(
    "/projects",
    response_model=PaginatedResponse[Project],
    summary="List all projects",
    description="Retrieve a paginated list of all projects.",
    responses={401: {"model": StandardError, "description": "Unauthorized"}},
)
async def list_projects(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    # Get total count
    total = db.scalar(select(func.count(ProjectModel.id)))

    # Get paginated projects
    offset = (page - 1) * limit
    projects = db.scalars(
        select(ProjectModel)
        .order_by(ProjectModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    pages = (total + limit - 1) // limit if total > 0 else 0

    return PaginatedResponse[Project](
        items=[Project.model_validate(p) for p in projects],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post(
    "/projects",
    response_model=Project,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="Create a new project linked to a git repository.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
    },
)
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    # Validate git URL is accessible
    _validate_git_url(str(project.git_url))

    # Create the project
    new_project = ProjectModel(
        name=project.name,
        git_url=str(project.git_url),
        main_branch=project.main_branch,
        triage_connection_id=project.triage_connection_id,
    )
    db.add(new_project)
    db.flush()

    # Create project settings
    _create_project_settings(db, new_project.id, project.settings)
    db.flush()

    # Refresh to get the settings relationship
    db.refresh(new_project)

    return Project.model_validate(new_project)


@router.get(
    "/projects/{project_id}",
    response_model=Project,
    summary="Get project by ID",
    description="Retrieve a specific project by its unique identifier.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Project not found"},
    },
)
async def get_project(project_id: UUID, db: Session = Depends(get_db)):
    project = get_or_404(db, ProjectModel, project_id)
    return Project.model_validate(project)


@router.patch(
    "/projects/{project_id}",
    response_model=Project,
    summary="Update project",
    description="Update an existing project's details.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Project not found"},
    },
)
async def update_project(
    project_id: UUID, project: ProjectUpdate, db: Session = Depends(get_db)
):
    db_project = get_or_404(db, ProjectModel, project_id)

    update_data = project.model_dump(exclude_unset=True)

    # If git_url is being updated, validate it
    if "git_url" in update_data:
        _validate_git_url(str(update_data["git_url"]))
        update_data["git_url"] = str(update_data["git_url"])

    if update_data:
        for key, value in update_data.items():
            setattr(db_project, key, value)

    db.flush()
    return Project.model_validate(db_project)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
    description="Delete a project and all associated plans and tasks.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Project not found"},
    },
)
async def delete_project(project_id: UUID, db: Session = Depends(get_db)):
    db_project = get_or_404(db, ProjectModel, project_id)
    db.delete(db_project)
    db.flush()


@router.get(
    "/projects/{project_id}/settings",
    response_model=ProjectSettings,
    summary="Get project settings",
    description="Retrieve the workflow settings for a project.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Project not found"},
    },
)
async def get_project_settings(project_id: UUID, db: Session = Depends(get_db)):
    project = get_or_404(db, ProjectModel, project_id)

    if not project.settings:
        raise HTTPException(status_code=404, detail="Project settings not found")

    return ProjectSettings.model_validate(project.settings)


@router.patch(
    "/projects/{project_id}/settings",
    response_model=ProjectSettings,
    summary="Update project settings",
    description="Update the workflow settings for a project.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Project not found"},
    },
)
async def update_project_settings(
    project_id: UUID, settings: ProjectSettingsUpdate, db: Session = Depends(get_db)
):
    project = get_or_404(db, ProjectModel, project_id)

    if not project.settings:
        raise HTTPException(status_code=404, detail="Project settings not found")

    update_data = settings.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(project.settings, key, value)

    db.flush()
    return ProjectSettings.model_validate(project.settings)
