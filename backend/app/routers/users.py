from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.auth import RequireAuth
from app.schemas import PaginatedResponse, StandardError, User

router = APIRouter()


@router.get(
    "/users",
    response_model=PaginatedResponse[User],
    summary="List users",
    description="Retrieve a paginated list of all users.",
    responses={401: {"model": StandardError, "description": "Unauthorized"}},
)
async def list_users(
    current_user: RequireAuth,
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/users/me",
    response_model=User,
    summary="Get current user",
    description="Retrieve the currently authenticated user's profile.",
    responses={401: {"model": StandardError, "description": "Unauthorized"}},
)
async def get_current_user_endpoint(current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def get_user(user_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")
