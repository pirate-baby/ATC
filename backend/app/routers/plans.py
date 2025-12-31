import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from app.models.enums import ProcessingStatus
from app.models.plan import Plan as PlanModel
from app.models.project import Project as ProjectModel
from app.models.review import Review as ReviewModel
from app.schemas import (
    PaginatedResponse,
    Plan,
    PlanCreate,
    PlanGenerateRequest,
    PlanGenerationStatus,
    PlanTaskStatus,
    PlanUpdate,
    PlanWithDetails,
    Review,
    ReviewCreate,
    ReviewDecision,
    SpawnedTaskSummary,
    SpawnTasksResponse,
    SpawnTasksStatus,
)
from app.schemas.plan import ReviewSummary, TaskSummary, ThreadSummary
from app.schemas.review import ReviewTargetType
from app.services.claude import claude_service
from app.services.task_queue import (
    is_job_running,
    submit_plan_generation,
    submit_task_spawning,
)

logger = logging.getLogger(__name__)

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
        processing_status=plan.processing_status,
        processing_error=plan.processing_error,
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


@router.post(
    "/plans/{plan_id}/generate",
    response_model=PlanGenerationStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate plan content",
    description="Submit a plan for AI-powered content generation using Claude.",
    responses={
        202: {"description": "Generation started"},
        409: {"description": "Generation already in progress"},
        503: {"description": "Claude service not configured"},
    },
)
async def generate_plan_content(
    plan_id: UUID,
    request: PlanGenerateRequest | None = None,
    db: Session = Depends(get_db),
):
    """Start AI-powered plan content generation.

    This endpoint initiates a background task to generate plan content using Claude.
    Poll the /plans/{plan_id}/generation-status endpoint to check progress.
    """
    plan = get_or_404(db, PlanModel, plan_id)

    # Check if Claude service is configured
    if not claude_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Claude service not configured. Set ANTHROPIC_API_KEY environment variable.",
        )

    # Check if generation is already in progress
    if plan.processing_status == ProcessingStatus.GENERATING:
        raise HTTPException(
            status_code=409,
            detail="Plan content generation already in progress",
        )

    # Check if there's an active job in the queue
    job_id = f"plan_gen_{plan_id}"
    if await is_job_running(job_id):
        raise HTTPException(
            status_code=409,
            detail="Plan content generation already in progress",
        )

    # Set status to generating
    plan.processing_status = ProcessingStatus.GENERATING
    plan.processing_error = None
    db.flush()

    # Build project context
    project = plan.project
    project_context = f"Project: {project.name}"

    # Get context from request
    context = request.context if request else None

    logger.info(
        f"Submitting plan generation job for plan {plan_id} ('{plan.title}') in project {project.name}"
    )

    # Submit to ARQ queue for background processing
    try:
        await submit_plan_generation(
            plan_id=plan_id,
            title=plan.title,
            context=context,
            project_context=project_context,
        )
        logger.info(f"Plan generation job successfully queued for plan {plan_id}")
    except Exception as e:
        logger.error(
            f"Failed to submit plan generation job for plan {plan_id}: {e!r}",
            exc_info=True,
        )
        plan.processing_status = ProcessingStatus.FAILED
        plan.processing_error = f"Failed to submit job: {e}"
        db.flush()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit plan generation: {e}",
        )

    return PlanGenerationStatus(
        plan_id=plan.id,
        processing_status=plan.processing_status,
        processing_error=plan.processing_error,
        content=plan.content,
    )


@router.get(
    "/plans/{plan_id}/generation-status",
    response_model=PlanGenerationStatus,
    summary="Get generation status",
    description="Check the status of plan content generation.",
    responses={
        200: {"description": "Current generation status"},
        404: {"description": "Plan not found"},
    },
)
async def get_plan_generation_status(
    plan_id: UUID,
    db: Session = Depends(get_db),
):
    """Get the current status of plan content generation.

    Poll this endpoint to track the progress of AI-powered plan generation.
    """
    plan = get_or_404(db, PlanModel, plan_id)

    return PlanGenerationStatus(
        plan_id=plan.id,
        processing_status=plan.processing_status,
        processing_error=plan.processing_error,
        content=plan.content,
    )


@router.post(
    "/plans/{plan_id}/spawn-tasks",
    response_model=SpawnTasksStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Spawn tasks from approved plan",
    description="Generate tasks from an approved plan using Claude AI.",
    responses={
        202: {"description": "Task spawning started"},
        400: {"description": "Plan has no content"},
        409: {"description": "Plan not approved or spawning already in progress"},
        503: {"description": "Claude service not configured"},
    },
)
async def spawn_tasks_from_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
):
    """Start AI-powered task generation from an approved plan.

    This endpoint initiates a background task to generate tasks using Claude.
    The plan must be in APPROVED status and have content.
    Poll the /plans/{plan_id}/spawn-status endpoint to check progress.
    """
    plan = get_or_404(db, PlanModel, plan_id)

    # Check if Claude service is configured
    if not claude_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Claude service not configured. Set ANTHROPIC_API_KEY environment variable.",
        )

    # Check if plan is approved
    if plan.status != PlanTaskStatus.APPROVED:
        raise HTTPException(
            status_code=409,
            detail=f"Plan must be in APPROVED status to spawn tasks. Current status: {plan.status.value}",
        )

    # Check if plan has content
    if not plan.content:
        raise HTTPException(
            status_code=400,
            detail="Plan has no content. Generate plan content first.",
        )

    # Check if task spawning is already in progress
    if plan.processing_status == ProcessingStatus.GENERATING:
        raise HTTPException(
            status_code=409,
            detail="Task spawning already in progress",
        )

    # Check if there's an active job in the queue
    job_id = f"task_spawn_{plan_id}"
    if await is_job_running(job_id):
        raise HTTPException(
            status_code=409,
            detail="Task spawning already in progress",
        )

    # Set status to generating
    plan.processing_status = ProcessingStatus.GENERATING
    plan.processing_error = None
    db.flush()

    # Build project context
    project = plan.project
    project_context = f"Project: {project.name}"

    logger.info(
        f"Submitting task spawning job for plan {plan_id} ('{plan.title}') in project {project.name}"
    )

    # Submit to ARQ queue for background processing
    try:
        await submit_task_spawning(
            plan_id=plan_id,
            title=plan.title,
            content=plan.content,
            project_id=plan.project_id,
            project_context=project_context,
        )
        logger.info(f"Task spawning job successfully queued for plan {plan_id}")
    except Exception as e:
        logger.error(
            f"Failed to submit task spawning job for plan {plan_id}: {e!r}",
            exc_info=True,
        )
        # Reset status and record error
        plan.processing_status = ProcessingStatus.COMPLETED
        plan.processing_error = f"Failed to queue task spawning: {str(e)}"
        db.flush()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue task spawning: {str(e)}",
        )

    return SpawnTasksStatus(
        plan_id=plan.id,
        processing_status=plan.processing_status,
        processing_error=plan.processing_error,
        tasks_created=None,
    )


@router.get(
    "/plans/{plan_id}/spawn-status",
    response_model=SpawnTasksStatus,
    summary="Get task spawning status",
    description="Check the status of task spawning from a plan.",
    responses={
        200: {"description": "Current spawning status"},
        404: {"description": "Plan not found"},
    },
)
async def get_spawn_tasks_status(
    plan_id: UUID,
    db: Session = Depends(get_db),
):
    """Get the current status of task spawning from a plan.

    Poll this endpoint to track the progress of AI-powered task generation.
    """
    plan = get_or_404(db, PlanModel, plan_id)

    tasks_created = None
    if plan.processing_status == ProcessingStatus.COMPLETED:
        tasks_created = len(plan.tasks)

    return SpawnTasksStatus(
        plan_id=plan.id,
        processing_status=plan.processing_status,
        processing_error=plan.processing_error,
        tasks_created=tasks_created,
    )


@router.get(
    "/plans/{plan_id}/spawned-tasks",
    response_model=SpawnTasksResponse,
    summary="Get spawned tasks",
    description="Get the list of tasks that were spawned from this plan.",
    responses={
        200: {"description": "List of spawned tasks"},
        404: {"description": "Plan not found"},
    },
)
async def get_spawned_tasks(
    plan_id: UUID,
    db: Session = Depends(get_db),
):
    """Get all tasks that were spawned from this plan."""
    plan = get_or_404(db, PlanModel, plan_id)

    tasks = [
        SpawnedTaskSummary(
            id=task.id,
            title=task.title,
            description=task.description,
            blocked_by=[t.id for t in task.blocked_by],
        )
        for task in plan.tasks
    ]

    return SpawnTasksResponse(
        plan_id=plan.id,
        tasks_created=len(tasks),
        tasks=tasks,
    )
