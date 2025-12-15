from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.plan import Plan as PlanModel
from app.models.project import Project as ProjectModel
from app.models.review import Review as ReviewModel
from app.schemas import (
    PaginatedResponse,
    Plan,
    PlanCreate,
    PlanTaskStatus,
    PlanUpdate,
    PlanWithDetails,
    Review,
    ReviewCreate,
    ReviewDecision,
    StandardError,
)
from app.schemas.plan import ReviewSummary, TaskSummary, ThreadSummary
from app.schemas.review import ReviewTargetType

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
    session: Session = Depends(get_session),
):
    project = ProjectModel.get_or_404(session, project_id)

    plans = project.plans
    if status is not None:
        plans = [p for p in plans if p.status == status.value]

    total = len(plans)
    offset = (page - 1) * limit
    items = plans[offset : offset + limit]
    pages = (total + limit - 1) // limit if total > 0 else 0

    return PaginatedResponse[Plan](
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


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
async def create_plan(project_id: UUID, plan: PlanCreate, session: Session = Depends(get_session)):
    ProjectModel.get_or_404(session, project_id)

    new_plan = PlanModel(
        project_id=project_id,
        title=plan.title,
        content=plan.content,
        parent_task_id=plan.parent_task_id,
    )
    session.add(new_plan)
    session.flush()
    return new_plan


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
async def get_plan(plan_id: UUID, session: Session = Depends(get_session)):
    plan = PlanModel.get_or_404(session, plan_id)

    tasks = [
        TaskSummary(id=task.id, title=task.title, status=PlanTaskStatus(task.status))
        for task in plan.tasks
    ]

    reviews = [
        ReviewSummary(
            id=review.id,
            reviewer_id=review.reviewer_id,
            decision=review.decision,
            created_at=review.created_at,
        )
        for review in plan.reviews
    ]

    threads = [
        ThreadSummary(id=thread.id, status=thread.status, comment_count=len(thread.comments))
        for thread in plan.threads
    ]

    return PlanWithDetails(
        id=plan.id,
        project_id=plan.project_id,
        title=plan.title,
        content=plan.content,
        status=PlanTaskStatus(plan.status),
        parent_task_id=plan.parent_task_id,
        version=plan.version,
        created_by=plan.created_by,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        tasks=tasks,
        reviews=reviews,
        threads=threads,
    )


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
async def update_plan(plan_id: UUID, plan: PlanUpdate, session: Session = Depends(get_session)):
    db_plan = PlanModel.get_or_404(session, plan_id)

    update_data = plan.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(db_plan, key, value)
        db_plan.version += 1

    session.flush()
    return db_plan


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
async def delete_plan(plan_id: UUID, session: Session = Depends(get_session)):
    db_plan = PlanModel.get_or_404(session, plan_id)
    session.delete(db_plan)
    session.flush()


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
async def list_plan_tasks(plan_id: UUID, session: Session = Depends(get_session)):
    plan = PlanModel.get_or_404(session, plan_id)
    return [
        TaskSummary(id=task.id, title=task.title, status=PlanTaskStatus(task.status))
        for task in plan.tasks
    ]


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
async def list_plan_reviews(plan_id: UUID, session: Session = Depends(get_session)):
    plan = PlanModel.get_or_404(session, plan_id)
    return plan.reviews


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
async def create_plan_review(
    plan_id: UUID,
    review: ReviewCreate,
    reviewer_id: UUID = Query(description="ID of the reviewer"),
    session: Session = Depends(get_session),
):
    plan = PlanModel.get_or_404(session, plan_id)

    if plan.status != PlanTaskStatus.REVIEW.value:
        raise HTTPException(status_code=409, detail="Plan not in review state")

    new_review = ReviewModel(
        target_type=ReviewTargetType.PLAN.value,
        target_id=plan_id,
        reviewer_id=reviewer_id,
        decision=review.decision.value,
        comment=review.comment,
    )
    session.add(new_review)
    session.flush()
    return new_review


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
async def approve_plan(plan_id: UUID, session: Session = Depends(get_session)):
    plan = PlanModel.get_or_404(session, plan_id)

    if plan.status != PlanTaskStatus.REVIEW.value:
        raise HTTPException(status_code=409, detail="Plan not in review state")

    project_settings = plan.project.settings
    required_approvals = project_settings.required_approvals_plan if project_settings else 1

    approval_count = sum(
        1 for review in plan.reviews if review.decision == ReviewDecision.APPROVED.value
    )

    if approval_count < required_approvals:
        raise HTTPException(
            status_code=409,
            detail=f"Insufficient approvals: {approval_count}/{required_approvals} required",
        )

    plan.status = PlanTaskStatus.APPROVED.value
    session.flush()
    return plan
