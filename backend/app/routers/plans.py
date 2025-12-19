from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas import (
    PaginatedResponse,
    Plan,
    PlanCreate,
    PlanTaskStatus,
    PlanUpdate,
    PlanWithDetails,
    Review,
    ReviewCreate,
    StandardError,
)
from app.schemas.plan import TaskSummary

router = APIRouter()


@router.get(
    "/projects/{project_id}/plans",
    response_model=PaginatedResponse[Plan],
    summary="List plans in project",
    description="Retrieve a paginated list of plans in a project with optional status filtering.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Project not found"},
    },
)
async def list_project_plans(
    project_id: UUID,
    status: PlanTaskStatus | None = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/projects/{project_id}/plans",
    response_model=Plan,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new plan",
    description="Create a new plan in the specified project.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Project not found"},
    },
)
async def create_plan(project_id: UUID, plan: PlanCreate):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/plans/{plan_id}",
    response_model=PlanWithDetails,
    summary="Get plan by ID",
    description="Retrieve a plan with full details including tasks, reviews, and threads.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Plan not found"},
    },
)
async def get_plan(plan_id: UUID):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch(
    "/plans/{plan_id}",
    response_model=Plan,
    summary="Update plan",
    description="Update an existing plan's title or content.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Plan not found"},
    },
)
async def update_plan(plan_id: UUID, plan: PlanUpdate):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete(
    "/plans/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete plan",
    description="Delete a plan and all associated tasks.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Plan not found"},
    },
)
async def delete_plan(plan_id: UUID):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/plans/{plan_id}/tasks",
    response_model=list[TaskSummary],
    summary="List tasks spawned by plan",
    description="Retrieve all tasks that were created from this plan.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Plan not found"},
    },
)
async def list_plan_tasks(plan_id: UUID):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/plans/{plan_id}/reviews",
    response_model=list[Review],
    summary="List plan reviews",
    description="Retrieve all reviews submitted for this plan.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Plan not found"},
    },
)
async def list_plan_reviews(plan_id: UUID):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/plans/{plan_id}/reviews",
    response_model=Review,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a plan review",
    description="Submit a review (approve, request changes, or comment) for a plan.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Plan not found"},
        409: {"model": StandardError, "description": "Plan not in review state"},
    },
)
async def create_plan_review(plan_id: UUID, review: ReviewCreate):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/plans/{plan_id}/approve",
    response_model=Plan,
    summary="Approve plan",
    description="Approve the plan after sufficient approvals. Creates tasks automatically.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Plan not found"},
        409: {
            "model": StandardError,
            "description": "Insufficient approvals or plan not in review state",
        },
    },
)
async def approve_plan(plan_id: UUID):
    raise HTTPException(status_code=501, detail="Not implemented")
