from collections import deque
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, get_or_404
from app.models.enums import PlanTaskStatus, ReviewDecision, ReviewTargetType
from app.models.plan import Plan as PlanModel
from app.models.project import Project as ProjectModel
from app.models.review import Review as ReviewModel
from app.models.task import Task as TaskModel
from app.models.task_image import TaskImage as TaskImageModel
from app.schemas import (
    CodeDiff,
    PaginatedResponse,
    Plan,
    Review,
    ReviewCreate,
    StandardError,
    StartSessionResponse,
    Task,
    TaskCreate,
    TaskImage,
    TaskUpdate,
    TaskWithDetails,
)
from app.schemas.common import PlanTaskStatus as SchemaPlanTaskStatus
from app.schemas.task import (
    BlockingTasksUpdate,
    ImageSummary,
    PlanSummary,
    ReviewSummary,
    SessionSummary,
    TaskSummary,
    ThreadSummary,
)
from app.services.git import (
    BranchExistsError,
    GitError,
    GitService,
    WorktreeExistsError,
)

router = APIRouter()


# =============================================================================
# Private Helper Functions
# =============================================================================


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
    if task_id in new_blocked_by:
        return True

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
                return True
            if blocker.id not in visited:
                queue.append(blocker.id)

    return False


def _validate_blocking_tasks(
    blocking_ids: list[UUID],
    project_id: UUID,
    db: Session,
) -> list[TaskModel]:
    """Validate that all blocking tasks exist and belong to the same project."""
    blocking_tasks: list[TaskModel] = []
    for blocking_id in blocking_ids:
        blocking_task = get_or_404(
            db, TaskModel, blocking_id, detail=f"Blocking task {blocking_id} not found"
        )
        if blocking_task.project_id != project_id:
            raise HTTPException(
                status_code=400,
                detail=f"Blocking task {blocking_id} belongs to a different project",
            )
        blocking_tasks.append(blocking_task)
    return blocking_tasks


def _has_incomplete_blockers(blocking_tasks: list[TaskModel]) -> bool:
    """Check if any blocking tasks are not yet complete."""
    return any(
        t.status not in (PlanTaskStatus.MERGED, PlanTaskStatus.CLOSED)
        for t in blocking_tasks
    )


def _apply_blocking_tasks(
    task: TaskModel,
    blocking_tasks: list[TaskModel],
    db: Session,
) -> None:
    """Apply blocking tasks to a task, checking for cycles and updating status."""
    if not blocking_tasks:
        return

    if _detect_cycle(task.id, [t.id for t in blocking_tasks], db):
        raise HTTPException(
            status_code=409,
            detail="Adding these blocking tasks would create a circular dependency",
        )

    task.blocked_by = blocking_tasks
    if _has_incomplete_blockers(blocking_tasks):
        task.status = PlanTaskStatus.BLOCKED


def _update_task_status_for_blockers(
    task: TaskModel,
    blocking_tasks: list[TaskModel],
) -> None:
    """Update task status based on presence and completion of blockers."""
    if blocking_tasks:
        if _has_incomplete_blockers(blocking_tasks) and task.status == PlanTaskStatus.BACKLOG:
            task.status = PlanTaskStatus.BLOCKED
    elif task.status == PlanTaskStatus.BLOCKED:
        task.status = PlanTaskStatus.BACKLOG


def _build_plan_summary(task: TaskModel) -> PlanSummary | None:
    """Build a plan summary from a task's parent plan."""
    if not task.plan:
        return None
    return PlanSummary(
        id=task.plan.id,
        title=task.plan.title,
        status=SchemaPlanTaskStatus(task.plan.status.value),
    )


def _build_blocking_tasks_summaries(task: TaskModel) -> list[TaskSummary]:
    """Build summaries of tasks that block this task."""
    return [
        TaskSummary(id=t.id, title=t.title, status=SchemaPlanTaskStatus(t.status.value))
        for t in task.blocked_by
    ]


def _build_reviews_summaries(task: TaskModel) -> list[ReviewSummary]:
    """Build summaries of reviews on this task."""
    return [
        ReviewSummary(
            id=r.id,
            reviewer_id=r.reviewer_id,
            decision=r.decision.value,
            created_at=r.created_at,
        )
        for r in task.reviews
    ]


def _build_threads_summaries(task: TaskModel) -> list[ThreadSummary]:
    """Build summaries of comment threads on this task."""
    return [
        ThreadSummary(id=t.id, status="open", comment_count=len(t.comments))
        for t in task.comment_threads
    ]


def _build_active_session(task: TaskModel) -> SessionSummary | None:
    """Build active session summary if task has an active session."""
    if not task.session_started_at or task.session_ended_at:
        return None
    return SessionSummary(
        id=task.id,
        status="active",
        started_at=task.session_started_at,
    )


def _copy_task_images_to_worktree(task: TaskModel, worktree_path: str) -> None:
    """
    Copy task images to the worktree so Claude Code can access them.

    Images are copied to .task-images/ directory in the worktree root.
    A manifest file is created listing all images with their descriptions.
    """
    from pathlib import Path
    import shutil
    import json

    if not task.images:
        return

    worktree = Path(worktree_path)
    images_dir = worktree / ".task-images"
    images_dir.mkdir(exist_ok=True)

    manifest = {
        "task_id": str(task.id),
        "task_title": task.title,
        "images": [],
    }

    for image in task.images:
        source_path = Path(image.storage_path)
        if source_path.exists():
            # Copy image to worktree
            dest_path = images_dir / image.original_filename
            # Handle duplicate filenames by adding a suffix
            counter = 1
            while dest_path.exists():
                stem = source_path.stem
                suffix = source_path.suffix
                dest_path = images_dir / f"{stem}_{counter}{suffix}"
                counter += 1

            shutil.copy2(source_path, dest_path)

            manifest["images"].append({
                "filename": dest_path.name,
                "original_filename": image.original_filename,
                "content_type": image.content_type,
                "path": str(dest_path.relative_to(worktree)),
            })

    # Write manifest file
    manifest_path = images_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))


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
        items=[Task.model_validate(t) for t in items],
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

    if task.plan_id is not None:
        get_or_404(db, PlanModel, task.plan_id, detail="Plan not found")

    blocking_tasks = _validate_blocking_tasks(task.blocked_by, project_id, db)

    new_task = TaskModel(
        project_id=project_id,
        plan_id=task.plan_id,
        title=task.title,
        description=task.description,
    )
    db.add(new_task)
    db.flush()

    _apply_blocking_tasks(new_task, blocking_tasks, db)

    db.flush()
    return Task.model_validate(new_task)


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
        plan=_build_plan_summary(task),
        blocking_tasks=_build_blocking_tasks_summaries(task),
        reviews=_build_reviews_summaries(task),
        threads=_build_threads_summaries(task),
        active_session=_build_active_session(task),
        images=[ImageSummary.model_validate(img) for img in task.images],
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
    return Task.model_validate(db_task)


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
    return _build_blocking_tasks_summaries(task)


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

    blocking_tasks = _validate_blocking_tasks(blocking.blocked_by, task.project_id, db)

    if _detect_cycle(task_id, blocking.blocked_by, db):
        raise HTTPException(
            status_code=409,
            detail="Setting these blocking tasks would create a circular dependency",
        )

    task.blocked_by = blocking_tasks
    task.version += 1

    _update_task_status_for_blockers(task, blocking_tasks)

    db.flush()
    return Task.model_validate(task)


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

    _update_blocked_tasks(task, db)

    return Task.model_validate(task)


def _update_blocked_tasks(completed_task: TaskModel, db: Session) -> None:
    """
    Update tasks that were blocked by the completed task.

    When a task reaches a terminal state (MERGED/CLOSED/CICD/APPROVED), check if any
    tasks that were blocked by it can now be unblocked.
    """
    terminal_states = (
        PlanTaskStatus.MERGED,
        PlanTaskStatus.CLOSED,
        PlanTaskStatus.CICD,
        PlanTaskStatus.APPROVED,
    )
    if completed_task.status not in terminal_states:
        return

    for blocked_task in completed_task.blocks:
        if blocked_task.status != PlanTaskStatus.BLOCKED:
            continue

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


@router.post(
    "/tasks/{task_id}/start-session",
    response_model=StartSessionResponse,
    summary="Start coding session",
    description="Create a git worktree and branch for this task, transitioning to coding status.",
    responses={
        400: {"model": StandardError, "description": "Task cannot start session (wrong status)"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
        409: {"model": StandardError, "description": "Worktree or branch already exists"},
    },
)
async def start_session(task_id: UUID, db: Session = Depends(get_db)):
    task = get_or_404(db, TaskModel, task_id)

    allowed_statuses = (PlanTaskStatus.BACKLOG,)
    if task.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start session for task in '{task.status.value}' status. "
            f"Task must be in one of: {', '.join(s.value for s in allowed_statuses)}",
        )

    if task.worktree_path or task.branch_name:
        raise HTTPException(
            status_code=409,
            detail="Task already has a worktree/branch. End the existing session first.",
        )

    project = task.project
    if not project.git_url:
        raise HTTPException(
            status_code=400,
            detail="Project does not have a git_url configured",
        )

    git_service = GitService(settings.worktrees_base_path)

    try:
        result = git_service.create_task_worktree(
            project_id=project.id,
            task_id=task.id,
            task_title=task.title,
            git_url=project.git_url,
            base_branch=project.main_branch,
        )
    except WorktreeExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except BranchExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except GitError as e:
        raise HTTPException(status_code=500, detail=f"Git operation failed: {e}")

    now = datetime.now(timezone.utc)
    task.worktree_path = result.worktree_path
    task.branch_name = result.branch_name
    task.status = PlanTaskStatus.CODING
    task.session_started_at = now
    task.version += 1

    # Copy task images to the worktree for Claude Code to access
    _copy_task_images_to_worktree(task, result.worktree_path)

    db.flush()

    return StartSessionResponse(
        task_id=task.id,
        branch_name=result.branch_name,
        worktree_path=result.worktree_path,
        status=SchemaPlanTaskStatus(task.status.value),
        session_started_at=now,
    )


@router.post(
    "/tasks/{task_id}/end-session",
    response_model=Task,
    summary="End coding session",
    description="Clean up the git worktree for this task. Does not delete the branch.",
    responses={
        400: {"model": StandardError, "description": "Task has no active session"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
    },
)
async def end_session(
    task_id: UUID,
    force: bool = Query(default=False, description="Force cleanup even with uncommitted changes"),
    db: Session = Depends(get_db),
):
    task = get_or_404(db, TaskModel, task_id)

    if not task.worktree_path:
        raise HTTPException(
            status_code=400,
            detail="Task does not have an active worktree session",
        )

    project = task.project
    git_service = GitService(settings.worktrees_base_path)

    try:
        git_service.cleanup_task_worktree(
            project_id=project.id,
            task_id=task.id,
            branch_name=task.branch_name,
            force=force,
            should_delete_branch=False,
        )
    except GitError as e:
        raise HTTPException(status_code=500, detail=f"Git cleanup failed: {e}")

    task.worktree_path = None
    task.session_ended_at = datetime.now(timezone.utc)
    task.version += 1

    db.flush()
    return Task.model_validate(task)


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
async def get_task_diff(
    task_id: UUID,
    include_lines: bool = Query(
        default=False,
        description="Include parsed line-level diff information for each file",
    ),
    db: Session = Depends(get_db),
):
    from app.schemas.task import DiffLine, DiffLineType
    from app.services.git import GitError, generate_diff, parse_patch_lines

    task = get_or_404(db, TaskModel, task_id)

    # Task must have a worktree path to generate diff
    if not task.worktree_path:
        raise HTTPException(
            status_code=404,
            detail="Task has no worktree - task may not have started coding yet",
        )

    if not task.branch_name:
        raise HTTPException(
            status_code=404,
            detail="Task has no branch - task may not have started coding yet",
        )

    # Get the base branch from the project
    base_branch = task.project.main_branch

    try:
        diff_result = generate_diff(
            repo_path=task.worktree_path,
            base_branch=base_branch,
            head_branch=task.branch_name,
        )
    except GitError as e:
        raise HTTPException(status_code=500, detail=f"Git error: {e}")

    # Build file diffs with optional line-level information
    from app.schemas.task import FileDiff as FileDiffSchema

    files = []
    total_additions = 0
    total_deletions = 0

    for file_diff in diff_result.files:
        total_additions += file_diff.additions
        total_deletions += file_diff.deletions

        lines = None
        if include_lines and file_diff.patch:
            parsed_lines = parse_patch_lines(file_diff.patch)
            lines = [
                DiffLine(
                    type=DiffLineType(line.type),
                    content=line.content,
                    old_line_number=line.old_line_number,
                    new_line_number=line.new_line_number,
                )
                for line in parsed_lines
            ]

        files.append(
            FileDiffSchema(
                path=file_diff.path,
                status=file_diff.status,
                additions=file_diff.additions,
                deletions=file_diff.deletions,
                patch=file_diff.patch,
                lines=lines,
            )
        )

    return CodeDiff(
        base_branch=diff_result.base_branch,
        head_branch=diff_result.head_branch,
        files=files,
        total_additions=total_additions,
        total_deletions=total_deletions,
    )


# =============================================================================
# Task Image Endpoints
# =============================================================================


@router.get(
    "/tasks/{task_id}/images",
    response_model=list[TaskImage],
    summary="List task images",
    description="Get all images attached to a task.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
    },
)
async def list_task_images(task_id: UUID, db: Session = Depends(get_db)):
    task = get_or_404(db, TaskModel, task_id)
    return [TaskImage.model_validate(img) for img in task.images]


@router.post(
    "/tasks/{task_id}/images",
    response_model=TaskImage,
    status_code=status.HTTP_201_CREATED,
    summary="Upload image to task",
    description="Upload an image attachment to a task for Claude Code to reference.",
    responses={
        400: {"model": StandardError, "description": "Invalid file type or size"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
    },
)
async def upload_task_image(
    task_id: UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    from uuid import uuid4

    task = get_or_404(db, TaskModel, task_id)

    # Validate content type
    if file.content_type not in settings.allowed_image_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(settings.allowed_image_types)}",
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > settings.max_image_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_image_size_bytes // (1024*1024)} MB",
        )

    # Generate unique filename
    file_ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin"
    unique_filename = f"{uuid4()}.{file_ext}"

    # Create storage directory for this task
    task_upload_dir = settings.uploads_base_path / "tasks" / str(task_id)
    task_upload_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    storage_path = task_upload_dir / unique_filename
    storage_path.write_bytes(content)

    # Create database record
    task_image = TaskImageModel(
        task_id=task_id,
        filename=unique_filename,
        original_filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        storage_path=str(storage_path),
    )
    db.add(task_image)
    db.flush()

    return TaskImage.model_validate(task_image)


@router.get(
    "/tasks/{task_id}/images/{image_id}",
    summary="Get task image",
    description="Download a task image by ID.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task or image not found"},
    },
)
async def get_task_image(task_id: UUID, image_id: UUID, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse

    task = get_or_404(db, TaskModel, task_id)

    # Find the image
    image = None
    for img in task.images:
        if img.id == image_id:
            image = img
            break

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Check if file exists
    from pathlib import Path

    if not Path(image.storage_path).exists():
        raise HTTPException(status_code=404, detail="Image file not found on disk")

    return FileResponse(
        path=image.storage_path,
        media_type=image.content_type,
        filename=image.original_filename,
    )


@router.delete(
    "/tasks/{task_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task image",
    description="Delete an image attachment from a task.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task or image not found"},
    },
)
async def delete_task_image(task_id: UUID, image_id: UUID, db: Session = Depends(get_db)):
    from pathlib import Path

    task = get_or_404(db, TaskModel, task_id)

    # Find the image
    image = None
    for img in task.images:
        if img.id == image_id:
            image = img
            break

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Delete file from disk
    file_path = Path(image.storage_path)
    if file_path.exists():
        file_path.unlink()

    # Delete from database
    db.delete(image)
    db.flush()
