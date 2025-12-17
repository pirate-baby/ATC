from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.auth import RequireAuth
from app.schemas import (
    Comment,
    CommentCreate,
    CommentThread,
    CommentThreadCreate,
    StandardError,
    TargetType,
)
from app.schemas.comment import CommentThreadWithComments

router = APIRouter()


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
async def list_plan_threads(plan_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def create_plan_thread(plan_id: UUID, current_user: RequireAuth, thread: CommentThreadCreate):
    raise HTTPException(status_code=501, detail="Not implemented")


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
    current_user: RequireAuth,
    target_type: TargetType | None = Query(
        default=None, description="Filter by target type (task or code_line)"
    ),
):
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def create_task_thread(task_id: UUID, current_user: RequireAuth, thread: CommentThreadCreate):
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def get_thread(thread_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/threads/{thread_id}/resolve",
    response_model=CommentThread,
    summary="Resolve thread",
    description="Resolve a comment thread. Triggers AI summarization of the discussion.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Thread not found"},
    },
)
async def resolve_thread(thread_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def list_thread_comments(thread_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def create_comment(thread_id: UUID, current_user: RequireAuth, comment: CommentCreate):
    raise HTTPException(status_code=501, detail="Not implemented")
