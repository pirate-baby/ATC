from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

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
):
    """List all projects with pagination."""
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def create_project(project: ProjectCreate):
    """Create a new project."""
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def get_project(project_id: UUID):
    """Get project by ID."""
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def update_project(project_id: UUID, project: ProjectUpdate):
    """Update a project."""
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def delete_project(project_id: UUID):
    """Delete a project."""
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def get_project_settings(project_id: UUID):
    """Get project settings."""
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def update_project_settings(project_id: UUID, settings: ProjectSettingsUpdate):
    """Update project settings."""
    raise HTTPException(status_code=501, detail="Not implemented")
