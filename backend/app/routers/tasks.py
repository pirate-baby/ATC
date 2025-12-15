from collections import deque
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from app.models.enums import PlanTaskStatus, ReviewDecision, ReviewTargetType
from app.models.plan import Plan as PlanModel
from app.models.project import Project as ProjectModel
from app.models.review import Review as ReviewModel
from app.models.task import Task as TaskModel
from app.schemas import (
    CodeDiff,
    PaginatedResponse,
    Plan,
    Review,
    ReviewCreate,
    StandardError,
    Task,
    TaskCreate,
    TaskUpdate,
    TaskWithDetails,
)
from app.schemas.common import PlanTaskStatus as SchemaPlanTaskStatus
from app.schemas.task import (
    BlockingTasksUpdate,
    PlanSummary,
    ReviewSummary,
    SessionSummary,
    TaskSummary,
    ThreadSummary,
)

router = APIRouter()


def _detect_cycle(
    task_id: UUID,
    new_blocked_by: list[UUID],
    session: Session,
) -> bool:
    """
    Detect if adding new_blocked_by to task_id would create a cycle in the DAG.

    Uses BFS to check if task_id is reachable from any of the new_blocked_by tasks
    following the blocked_by relationships. If task_id is reachable, adding the
    new edges would create a cycle.
    """
    if not new_blocked_by:
        return False

    # If task blocks itself directly
    if task_id in new_blocked_by:
        return True

    # BFS from each new blocking task to see if we can reach task_id
    visited: set[UUID] = set()
    queue: deque[UUID] = deque(new_blocked_by)

    while queue:
        current_id = queue.popleft()
        if current_id in visited:
            continue
        visited.add(current_id)

        current_task = session.get(TaskModel, current_id)
        if current_task is None:
            continue

        for blocker in current_task.blocked_by:
            if blocker.id == task_id:
                # Found a path back to task_id - cycle detected
                return True
            if blocker.id not in visited:
                queue.append(blocker.id)

    return False


def _task_to_response(task: TaskModel) -> Task:
    """Convert a Task model to a Task response schema."""
    return Task(
        id=task.id,
        project_id=task.project_id,
        plan_id=task.plan_id,
        title=task.title,
        description=task.description,
        status=SchemaPlanTaskStatus(task.status.value),
        blocked_by=[t.id for t in task.blocked_by],
        branch_name=task.branch_name,
        worktree_path=task.worktree_path,
        version=task.version,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


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
    status: SchemaPlanTaskStatus | None = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    project = get_or_404(db, ProjectModel, project_id)

    tasks = project.tasks
    if status is not None:
        tasks = [t for t in tasks if t.status == PlanTaskStatus(status.value)]

    total = len(tasks)
    offset = (page - 1) * limit
    items = tasks[offset : offset + limit]
    pages = (total + limit - 1) // limit if total > 0 else 0

    return PaginatedResponse[Task](
        items=[_task_to_response(t) for t in items],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


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
async def create_task(
    project_id: UUID,
    task: TaskCreate,
    db: Session = Depends(get_db),
):
    get_or_404(db, ProjectModel, project_id)

    # Validate plan_id if provided
    if task.plan_id is not None:
        get_or_404(db, PlanModel, task.plan_id, detail="Plan not found")

    # Validate blocked_by tasks exist and belong to same project
    blocking_tasks: list[TaskModel] = []
    for blocking_id in task.blocked_by:
        blocking_task = get_or_404(
            db, TaskModel, blocking_id, detail=f"Blocking task {blocking_id} not found"
        )
        if blocking_task.project_id != project_id:
            raise HTTPException(
                status_code=400,
                detail=f"Blocking task {blocking_id} belongs to a different project",
            )
        blocking_tasks.append(blocking_task)

    # Create the task first (without blocked_by to avoid issues)
    new_task = TaskModel(
        project_id=project_id,
        plan_id=task.plan_id,
        title=task.title,
        description=task.description,
    )
    db.add(new_task)
    db.flush()

    # Now check for cycles if there are blocking tasks
    if blocking_tasks:
        # Check if adding these blockers would create a cycle
        if _detect_cycle(new_task.id, [t.id for t in blocking_tasks], db):
            raise HTTPException(
                status_code=409,
                detail="Adding these blocking tasks would create a circular dependency",
            )
        new_task.blocked_by = blocking_tasks

        # Update status to blocked if there are incomplete blockers
        incomplete_blockers = [
            t
            for t in blocking_tasks
            if t.status not in (PlanTaskStatus.MERGED, PlanTaskStatus.CLOSED)
        ]
        if incomplete_blockers:
            new_task.status = PlanTaskStatus.BLOCKED

    db.flush()
    return _task_to_response(new_task)


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
async def get_task(task_id: UUID, db: Session = Depends(get_db)):
    task = get_or_404(db, TaskModel, task_id)

    # Build plan summary
    plan_summary = None
    if task.plan:
        plan_summary = PlanSummary(
            id=task.plan.id,
            title=task.plan.title,
            status=SchemaPlanTaskStatus(task.plan.status.value),
        )

    # Build blocking tasks summaries
    blocking_tasks = [
        TaskSummary(id=t.id, title=t.title, status=SchemaPlanTaskStatus(t.status.value))
        for t in task.blocked_by
    ]

    # Build reviews summaries
    reviews = [
        ReviewSummary(
            id=r.id,
            reviewer_id=r.reviewer_id,
            decision=r.decision.value,
            created_at=r.created_at,
        )
        for r in task.reviews
    ]

    # Build threads summaries
    threads = [
        ThreadSummary(id=t.id, status=t.status.value, comment_count=len(t.comments))
        for t in task.comment_threads
    ]

    # Get active session info from task fields
    active_session = None
    if task.session_started_at and not task.session_ended_at:
        active_session = SessionSummary(
            id=task.id,  # Use task ID as session ID since merged
            status="active",
            started_at=task.session_started_at,
        )

    return TaskWithDetails(
        id=task.id,
        project_id=task.project_id,
        plan_id=task.plan_id,
        title=task.title,
        description=task.description,
        status=SchemaPlanTaskStatus(task.status.value),
        blocked_by=[t.id for t in task.blocked_by],
        branch_name=task.branch_name,
        worktree_path=task.worktree_path,
        version=task.version,
        created_at=task.created_at,
        updated_at=task.updated_at,
        plan=plan_summary,
        blocking_tasks=blocking_tasks,
        reviews=reviews,
        threads=threads,
        active_session=active_session,
    )


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
async def update_task(
    task_id: UUID,
    task: TaskUpdate,
    db: Session = Depends(get_db),
):
    db_task = get_or_404(db, TaskModel, task_id)

    update_data = task.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(db_task, key, value)
        db_task.version += 1

    db.flush()
    return _task_to_response(db_task)


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
async def delete_task(task_id: UUID, db: Session = Depends(get_db)):
    db_task = get_or_404(db, TaskModel, task_id)
    db.delete(db_task)
    db.flush()


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
async def get_blocking_tasks(task_id: UUID, db: Session = Depends(get_db)):
    task = get_or_404(db, TaskModel, task_id)
    return [
        TaskSummary(id=t.id, title=t.title, status=SchemaPlanTaskStatus(t.status.value))
        for t in task.blocked_by
    ]


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
    task_id: UUID,
    blocking: BlockingTasksUpdate,
    db: Session = Depends(get_db),
):
    task = get_or_404(db, TaskModel, task_id)

    # Validate all blocking tasks exist and belong to same project
    blocking_tasks: list[TaskModel] = []
    for blocking_id in blocking.blocked_by:
        blocking_task = get_or_404(
            db, TaskModel, blocking_id, detail=f"Blocking task {blocking_id} not found"
        )
        if blocking_task.project_id != task.project_id:
            raise HTTPException(
                status_code=400,
                detail=f"Blocking task {blocking_id} belongs to a different project",
            )
        blocking_tasks.append(blocking_task)

    # Check for circular dependencies
    if _detect_cycle(task_id, blocking.blocked_by, db):
        raise HTTPException(
            status_code=409,
            detail="Setting these blocking tasks would create a circular dependency",
        )

    # Update the blocked_by relationship
    task.blocked_by = blocking_tasks
    task.version += 1

    # Update status based on blockers
    if blocking_tasks:
        incomplete_blockers = [
            t
            for t in blocking_tasks
            if t.status not in (PlanTaskStatus.MERGED, PlanTaskStatus.CLOSED)
        ]
        if incomplete_blockers and task.status == PlanTaskStatus.BACKLOG:
            task.status = PlanTaskStatus.BLOCKED
    else:
        # No blockers - if task was blocked, move back to backlog
        if task.status == PlanTaskStatus.BLOCKED:
            task.status = PlanTaskStatus.BACKLOG

    db.flush()
    return _task_to_response(task)


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
async def list_task_reviews(task_id: UUID, db: Session = Depends(get_db)):
    task = get_or_404(db, TaskModel, task_id)
    return task.reviews


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
async def create_task_review(
    task_id: UUID,
    review: ReviewCreate,
    reviewer_id: UUID = Query(description="ID of the reviewer"),
    db: Session = Depends(get_db),
):
    task = get_or_404(db, TaskModel, task_id)

    if task.status != PlanTaskStatus.REVIEW:
        raise HTTPException(status_code=409, detail="Task not in review state")

    new_review = ReviewModel(
        target_type=ReviewTargetType.TASK,
        target_id=task_id,
        reviewer_id=reviewer_id,
        decision=ReviewDecision(review.decision.value),
        comment=review.comment,
    )
    db.add(new_review)
    db.flush()
    return new_review


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
async def approve_task(task_id: UUID, db: Session = Depends(get_db)):
    task = get_or_404(db, TaskModel, task_id)

    if task.status != PlanTaskStatus.REVIEW:
        raise HTTPException(status_code=409, detail="Task not in review state")

    project_settings = task.project.settings
    required_approvals = project_settings.required_approvals_task if project_settings else 1

    approval_count = sum(1 for review in task.reviews if review.decision == ReviewDecision.APPROVED)

    if approval_count < required_approvals:
        raise HTTPException(
            status_code=409,
            detail=f"Insufficient approvals: {approval_count}/{required_approvals} required",
        )

    task.status = PlanTaskStatus.CICD
    task.version += 1
    db.flush()

    # Check if any tasks were blocked by this task and update them
    _update_blocked_tasks(task, db)

    return _task_to_response(task)


def _update_blocked_tasks(completed_task: TaskModel, db: Session):
    """
    When a task reaches a terminal state (MERGED/CLOSED), check if any
    tasks that were blocked by it can now be unblocked.
    """
    if completed_task.status not in (
        PlanTaskStatus.MERGED,
        PlanTaskStatus.CLOSED,
        PlanTaskStatus.CICD,
        PlanTaskStatus.APPROVED,
    ):
        return

    # Find tasks that this task blocks
    for blocked_task in completed_task.blocks:
        if blocked_task.status != PlanTaskStatus.BLOCKED:
            continue

        # Check if all blockers are now complete
        all_blockers_complete = all(
            blocker.status in (PlanTaskStatus.MERGED, PlanTaskStatus.CLOSED)
            for blocker in blocked_task.blocked_by
        )

        if all_blockers_complete:
            blocked_task.status = PlanTaskStatus.BACKLOG
            blocked_task.version += 1


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
async def spawn_plan_from_task(task_id: UUID, db: Session = Depends(get_db)):
    task = get_or_404(db, TaskModel, task_id)

    new_plan = PlanModel(
        project_id=task.project_id,
        title=f"Sub-plan: {task.title}",
        content=task.description,
        parent_task_id=task_id,
    )
    db.add(new_plan)
    db.flush()
    return new_plan


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
async def get_task_diff(task_id: UUID, db: Session = Depends(get_db)):
    # Verify task exists
    get_or_404(db, TaskModel, task_id)

    # Stub implementation - returns 501 as per requirements
    raise HTTPException(status_code=501, detail="Not implemented")
