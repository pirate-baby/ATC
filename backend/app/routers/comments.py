from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import RequireAuth
from app.database import get_db, get_or_404
from app.models.comment import Comment as CommentModel
from app.models.comment import CommentThread as CommentThreadModel
from app.models.enums import CommentThreadStatus, CommentThreadTargetType
from app.models.plan import Plan as PlanModel
from app.models.task import Task as TaskModel
from app.models.user import User as UserModel
from app.schemas import (
    Comment,
    CommentCreate,
    CommentThread,
    CommentThreadCreate,
    StandardError,
    TargetType,
)
from app.schemas.comment import CommentThreadStatus as SchemaCommentThreadStatus
from app.schemas.comment import CommentThreadWithComments

router = APIRouter()


# =============================================================================
# Private Helper Functions
# =============================================================================


def _schema_target_type_to_model(target_type: TargetType) -> CommentThreadTargetType:
    """Convert schema TargetType to model CommentThreadTargetType."""
    if target_type == TargetType.CODE_LINE:
        return CommentThreadTargetType.LINE
    return CommentThreadTargetType(target_type.value)


def _model_target_type_to_schema(target_type: CommentThreadTargetType) -> TargetType:
    """Convert model CommentThreadTargetType to schema TargetType."""
    if target_type == CommentThreadTargetType.LINE:
        return TargetType.CODE_LINE
    return TargetType(target_type.value)


def _model_status_to_schema(status: CommentThreadStatus) -> SchemaCommentThreadStatus:
    """Convert model CommentThreadStatus to schema CommentThreadStatus."""
    return SchemaCommentThreadStatus(status.value)


def _build_comment_thread_response(thread: CommentThreadModel) -> CommentThread:
    """Build a CommentThread schema from a model."""
    return CommentThread(
        id=thread.id,
        target_id=thread.target_id,
        target_type=_model_target_type_to_schema(thread.target_type),
        file_path=thread.file_path,
        line_number=thread.line_number,
        status=_model_status_to_schema(thread.status),
        summary=thread.summary,
        created_at=thread.created_at,
    )


def _build_comment_thread_with_comments_response(
    thread: CommentThreadModel,
) -> CommentThreadWithComments:
    """Build a CommentThreadWithComments schema from a model."""
    return CommentThreadWithComments(
        id=thread.id,
        target_id=thread.target_id,
        target_type=_model_target_type_to_schema(thread.target_type),
        file_path=thread.file_path,
        line_number=thread.line_number,
        status=_model_status_to_schema(thread.status),
        summary=thread.summary,
        created_at=thread.created_at,
        comments=[Comment.model_validate(c) for c in thread.comments],
    )


def _validate_code_line_fields(thread: CommentThreadCreate) -> None:
    """Validate that code_line threads have required file_path and line_number."""
    if thread.target_type == TargetType.CODE_LINE:
        if not thread.file_path:
            raise HTTPException(
                status_code=400,
                detail="file_path is required for code_line threads",
            )
        if thread.line_number is None:
            raise HTTPException(
                status_code=400,
                detail="line_number is required for code_line threads",
            )


def _validate_parent_comment(
    parent_comment_id: UUID | None,
    thread_id: UUID,
    db: Session,
) -> None:
    """Validate that parent_comment_id exists and belongs to the same thread."""
    if parent_comment_id is None:
        return

    parent_comment = db.get(CommentModel, parent_comment_id)
    if parent_comment is None:
        raise HTTPException(
            status_code=400,
            detail=f"Parent comment {parent_comment_id} not found",
        )
    if parent_comment.thread_id != thread_id:
        raise HTTPException(
            status_code=400,
            detail="Parent comment does not belong to the same thread",
        )


# =============================================================================
# Plan Thread Endpoints
# =============================================================================


@router.get(
    "/plans/{plan_id}/threads",
    response_model=list[CommentThread],
    summary="List plan comment threads",
    description="Retrieve all comment threads attached to a plan.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Plan not found"},
    },
)
async def list_plan_threads(plan_id: UUID, db: Session = Depends(get_db)):
    plan = get_or_404(db, PlanModel, plan_id)
    return [_build_comment_thread_response(t) for t in plan.comment_threads]


@router.post(
    "/plans/{plan_id}/threads",
    response_model=CommentThread,
    status_code=status.HTTP_201_CREATED,
    summary="Create plan comment thread",
    description="Create a new comment thread on a plan.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Plan not found"},
    },
)
async def create_plan_thread(
    plan_id: UUID,
    thread: CommentThreadCreate,
    current_user: RequireAuth,
    db: Session = Depends(get_db),
):
    # Validate plan exists
    get_or_404(db, PlanModel, plan_id)

    # Validate target_type is 'plan'
    if thread.target_type != TargetType.PLAN:
        raise HTTPException(
            status_code=400,
            detail="target_type must be 'plan' for plan threads",
        )

    # Create the thread
    new_thread = CommentThreadModel(
        target_type=CommentThreadTargetType.PLAN,
        target_id=plan_id,
        file_path=thread.file_path,
        line_number=thread.line_number,
    )
    db.add(new_thread)
    db.flush()

    # Create the initial comment
    initial_comment = CommentModel(
        thread_id=new_thread.id,
        author_id=current_user.id,
        content=thread.initial_comment,
    )
    db.add(initial_comment)
    db.flush()

    return _build_comment_thread_response(new_thread)


# =============================================================================
# Task Thread Endpoints
# =============================================================================


@router.get(
    "/tasks/{task_id}/threads",
    response_model=list[CommentThread],
    summary="List task comment threads",
    description="Retrieve all comment threads attached to a task. Filter by type.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
    },
)
async def list_task_threads(
    task_id: UUID,
    target_type: TargetType | None = Query(
        default=None, description="Filter by target type (task or code_line)"
    ),
    db: Session = Depends(get_db),
):
    task = get_or_404(db, TaskModel, task_id)
    threads = task.comment_threads

    # Filter by target_type if specified
    if target_type is not None:
        model_target_type = _schema_target_type_to_model(target_type)
        threads = [t for t in threads if t.target_type == model_target_type]

    return [_build_comment_thread_response(t) for t in threads]


@router.post(
    "/tasks/{task_id}/threads",
    response_model=CommentThread,
    status_code=status.HTTP_201_CREATED,
    summary="Create task comment thread",
    description="Create a new comment thread on a task or a specific code line.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Task not found"},
    },
)
async def create_task_thread(
    task_id: UUID,
    thread: CommentThreadCreate,
    current_user: RequireAuth,
    db: Session = Depends(get_db),
):
    # Validate task exists
    get_or_404(db, TaskModel, task_id)

    # Validate target_type is 'task' or 'code_line'
    if thread.target_type not in (TargetType.TASK, TargetType.CODE_LINE):
        raise HTTPException(
            status_code=400,
            detail="target_type must be 'task' or 'code_line' for task threads",
        )

    # Validate code_line specific fields
    _validate_code_line_fields(thread)

    # Create the thread
    new_thread = CommentThreadModel(
        target_type=_schema_target_type_to_model(thread.target_type),
        target_id=task_id,
        file_path=thread.file_path,
        line_number=thread.line_number,
    )
    db.add(new_thread)
    db.flush()

    # Create the initial comment
    initial_comment = CommentModel(
        thread_id=new_thread.id,
        author_id=current_user.id,
        content=thread.initial_comment,
    )
    db.add(initial_comment)
    db.flush()

    return _build_comment_thread_response(new_thread)


# =============================================================================
# Thread Endpoints
# =============================================================================


@router.get(
    "/threads/{thread_id}",
    response_model=CommentThreadWithComments,
    summary="Get thread with comments",
    description="Retrieve a comment thread with all its comments.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Thread not found"},
    },
)
async def get_thread(thread_id: UUID, db: Session = Depends(get_db)):
    thread = get_or_404(db, CommentThreadModel, thread_id)
    return _build_comment_thread_with_comments_response(thread)


@router.post(
    "/threads/{thread_id}/resolve",
    response_model=CommentThread,
    summary="Resolve thread",
    description="Resolve a comment thread. Triggers AI summarization of the discussion.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Thread not found"},
        409: {"model": StandardError, "description": "Thread already resolved"},
    },
)
async def resolve_thread(thread_id: UUID, db: Session = Depends(get_db)):
    thread = get_or_404(db, CommentThreadModel, thread_id)

    if thread.status != CommentThreadStatus.OPEN:
        raise HTTPException(
            status_code=409,
            detail=f"Thread is already {thread.status.value}",
        )

    # Update thread status to resolved
    # AI summarization is deferred - just set status for now
    thread.status = CommentThreadStatus.RESOLVED
    db.flush()

    return _build_comment_thread_response(thread)


@router.get(
    "/threads/{thread_id}/comments",
    response_model=list[Comment],
    summary="List thread comments",
    description="List all comments in a thread.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Thread not found"},
    },
)
async def list_thread_comments(thread_id: UUID, db: Session = Depends(get_db)):
    thread = get_or_404(db, CommentThreadModel, thread_id)
    return [Comment.model_validate(c) for c in thread.comments]


@router.post(
    "/threads/{thread_id}/comments",
    response_model=Comment,
    status_code=status.HTTP_201_CREATED,
    summary="Add comment to thread",
    description="Add a new comment to an existing thread.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Thread not found"},
    },
)
async def create_comment(
    thread_id: UUID,
    comment: CommentCreate,
    current_user: RequireAuth,
    db: Session = Depends(get_db),
):
    # Validate thread exists
    get_or_404(db, CommentThreadModel, thread_id)

    # Validate parent_comment_id if provided
    _validate_parent_comment(comment.parent_comment_id, thread_id, db)

    # Create the comment
    new_comment = CommentModel(
        thread_id=thread_id,
        author_id=current_user.id,
        content=comment.content,
        parent_comment_id=comment.parent_comment_id,
    )
    db.add(new_comment)
    db.flush()

    return Comment.model_validate(new_comment)
