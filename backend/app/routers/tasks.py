from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.auth import RequireAuth
from app.schemas import (
    CodeDiff,
    PaginatedResponse,
    Plan,
    PlanTaskStatus,
    Review,
    ReviewCreate,
    StandardError,
    Task,
    TaskCreate,
    TaskUpdate,
    TaskWithDetails,
)
from app.schemas.task import BlockingTasksUpdate, TaskSummary

router = APIRouter()


@router.get(
    "/projects/{project_id}/tasks",
    response_model=PaginatedResponse[Task],
    summary="List tasks in project",
    description="Retrieve a paginated list of tasks in a project with optional status filtering.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Project not found"},
    },
)
async def list_project_tasks(
    project_id: UUID,
    current_user: RequireAuth,
    status: PlanTaskStatus | None = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/projects/{project_id}/tasks",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    description="Create a new task in the specified project.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Project not found"},
        409: {"model": StandardError, "description": "Circular dependency detected"},
    },
)
async def create_task(project_id: UUID, current_user: RequireAuth, task: TaskCreate):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/tasks/{task_id}",
    response_model=TaskWithDetails,
    summary="Get task by ID",
    description="Retrieve a task with full details including plan, blocking tasks, and reviews.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
    },
)
async def get_task(task_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch(
    "/tasks/{task_id}",
    response_model=Task,
    summary="Update task",
    description="Update an existing task's title or description.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
    },
)
async def update_task(task_id: UUID, current_user: RequireAuth, task: TaskUpdate):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    description="Delete a task.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
    },
)
async def delete_task(task_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/tasks/{task_id}/blocking",
    response_model=list[TaskSummary],
    summary="Get blocking tasks",
    description="Get the list of tasks that must complete before this task can start.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
    },
)
async def get_blocking_tasks(task_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.put(
    "/tasks/{task_id}/blocking",
    response_model=Task,
    summary="Set blocking tasks",
    description="Set blocking tasks. Validates no circular dependencies in the task DAG.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
        409: {"model": StandardError, "description": "Circular dependency would be created"},
    },
)
async def set_blocking_tasks(
    task_id: UUID, current_user: RequireAuth, blocking: BlockingTasksUpdate
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/tasks/{task_id}/reviews",
    response_model=list[Review],
    summary="List task reviews",
    description="Retrieve all reviews submitted for this task.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
    },
)
async def list_task_reviews(task_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/tasks/{task_id}/reviews",
    response_model=Review,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a task review",
    description="Submit a review (approve, request changes, or comment) for a task.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
        409: {"model": StandardError, "description": "Task not in review state"},
    },
)
async def create_task_review(task_id: UUID, current_user: RequireAuth, review: ReviewCreate):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/tasks/{task_id}/approve",
    response_model=Task,
    summary="Approve task",
    description="Approve the task after sufficient approvals. Pushes to CI/CD state.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
        409: {
            "model": StandardError,
            "description": "Insufficient approvals or task not in review state",
        },
    },
)
async def approve_task(task_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/tasks/{task_id}/spawn-plan",
    response_model=Plan,
    status_code=status.HTTP_201_CREATED,
    summary="Spawn sub-plan from task",
    description="Create a new plan from a complex task that needs further breakdown.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
    },
)
async def spawn_plan_from_task(task_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/tasks/{task_id}/diff",
    response_model=CodeDiff,
    summary="Get code diff",
    description="Get the git diff of changes made by this task compared to the base branch.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found or no branch exists"},
    },
)
async def get_task_diff(task_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")
