from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
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
)
from app.schemas.plan import ReviewSummary, TaskSummary, ThreadSummary
from app.schemas.review import ReviewTargetType

router = APIRouter()


@router.get("/projects/{project_id}/plans", response_model=PaginatedResponse[Plan])
async def list_project_plans(
    project_id: UUID,
    status: PlanTaskStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    project = get_or_404(db, ProjectModel, project_id)

    plans = project.plans
    if status is not None:
        plans = [p for p in plans if p.status == status]

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
)
async def create_plan(
    project_id: UUID, plan: PlanCreate, db: Session = Depends(get_db)
):
    get_or_404(db, ProjectModel, project_id)

    new_plan = PlanModel(
        project_id=project_id,
        title=plan.title,
        content=plan.content,
        parent_task_id=plan.parent_task_id,
    )
    db.add(new_plan)
    db.flush()
    return new_plan


@router.get("/plans/{plan_id}", response_model=PlanWithDetails)
async def get_plan(plan_id: UUID, db: Session = Depends(get_db)):
    plan = get_or_404(db, PlanModel, plan_id)

    tasks = [
        TaskSummary(id=task.id, title=task.title, status=task.status)
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
        ThreadSummary(
            id=thread.id, status=thread.target_type.value, comment_count=len(thread.comments)
        )
        for thread in plan.comment_threads
    ]

    return PlanWithDetails(
        id=plan.id,
        project_id=plan.project_id,
        title=plan.title,
        content=plan.content,
        status=plan.status,
        parent_task_id=plan.parent_task_id,
        version=plan.version,
        created_by=plan.created_by,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        tasks=tasks,
        reviews=reviews,
        threads=threads,
    )


@router.patch("/plans/{plan_id}", response_model=Plan)
async def update_plan(plan_id: UUID, plan: PlanUpdate, db: Session = Depends(get_db)):
    db_plan = get_or_404(db, PlanModel, plan_id)

    update_data = plan.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(db_plan, key, value)
        db_plan.version += 1

    db.flush()
    return db_plan


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(plan_id: UUID, db: Session = Depends(get_db)):
    db_plan = get_or_404(db, PlanModel, plan_id)
    db.delete(db_plan)
    db.flush()


@router.get("/plans/{plan_id}/tasks", response_model=list[TaskSummary])
async def list_plan_tasks(plan_id: UUID, db: Session = Depends(get_db)):
    plan = get_or_404(db, PlanModel, plan_id)
    return [
        TaskSummary(id=task.id, title=task.title, status=task.status)
        for task in plan.tasks
    ]


@router.get("/plans/{plan_id}/reviews", response_model=list[Review])
async def list_plan_reviews(plan_id: UUID, db: Session = Depends(get_db)):
    plan = get_or_404(db, PlanModel, plan_id)
    return plan.reviews


@router.post(
    "/plans/{plan_id}/reviews",
    response_model=Review,
    status_code=status.HTTP_201_CREATED,
)
async def create_plan_review(
    plan_id: UUID,
    review: ReviewCreate,
    reviewer_id: UUID = Query(description="ID of the reviewer"),
    db: Session = Depends(get_db),
):
    plan = get_or_404(db, PlanModel, plan_id)

    if plan.status != PlanTaskStatus.REVIEW:
        raise HTTPException(status_code=409, detail="Plan not in review state")

    new_review = ReviewModel(
        target_type=ReviewTargetType.PLAN,
        target_id=plan_id,
        reviewer_id=reviewer_id,
        decision=review.decision,
        comment=review.comment,
    )
    db.add(new_review)
    db.flush()
    return new_review


@router.post("/plans/{plan_id}/approve", response_model=Plan)
async def approve_plan(plan_id: UUID, db: Session = Depends(get_db)):
    plan = get_or_404(db, PlanModel, plan_id)

    if plan.status != PlanTaskStatus.REVIEW:
        raise HTTPException(status_code=409, detail="Plan not in review state")

    project_settings = plan.project.settings
    required_approvals = project_settings.required_approvals_plan if project_settings else 1

    approval_count = sum(
        1 for review in plan.reviews if review.decision == ReviewDecision.APPROVED
    )

    if approval_count < required_approvals:
        raise HTTPException(
            status_code=409,
            detail=f"Insufficient approvals: {approval_count}/{required_approvals} required",
        )

    plan.status = PlanTaskStatus.APPROVED
    db.flush()
    return plan
