from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.user import User as UserModel
from app.schemas import PaginatedResponse, StandardError, User

router = APIRouter()

MOCK_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


@router.get(
    "/users",
    response_model=PaginatedResponse[User],
    summary="List users",
    description="Retrieve a paginated list of all users.",
    responses={401: {"model": StandardError, "description": "Unauthorized"}},
)
async def list_users(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_session),
):
    offset = (page - 1) * limit

    items = session.scalars(select(UserModel).offset(offset).limit(limit)).all()
    total = session.scalar(select(func.count()).select_from(UserModel)) or 0
    pages = (total + limit - 1) // limit if total > 0 else 0

    return PaginatedResponse[User](
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get(
    "/users/me",
    response_model=User,
    summary="Get current user",
    description="Retrieve the currently authenticated user's profile. "
    "Returns a placeholder user until authentication is implemented.",
    responses={401: {"model": StandardError, "description": "Unauthorized"}},
)
async def get_current_user():
    return User(
        id=MOCK_USER_ID,
        git_handle="current_user",
        email="current_user@example.com",
        display_name="Current User (placeholder)",
        avatar_url=None,
        created_at=datetime.now(timezone.utc),
    )


@router.get(
    "/users/{user_id}",
    response_model=User,
    summary="Get user by ID",
    description="Retrieve a specific user by their unique identifier.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "User not found"},
    },
)
async def get_user(user_id: UUID, session: Session = Depends(get_session)):
    return UserModel.get_or_404(session, user_id)
