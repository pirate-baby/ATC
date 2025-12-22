from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User as UserModel
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
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/users/me",
    response_model=User,
    summary="Get current user",
    description="""
Retrieve the currently authenticated user's profile.

## Impersonation

Admins can impersonate other users by passing the `X-Impersonate-User` header
with the target user's ID. This is useful for testing and debugging.
""",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "User not found"},
    },
)
async def get_current_user_endpoint(
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request)

    impersonate_user_id = request.headers.get("X-Impersonate-User")
    if impersonate_user_id:
        try:
            target_user_id = UUID(impersonate_user_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid X-Impersonate-User header: must be a valid UUID",
            )
        user = db.query(UserModel).filter(UserModel.id == target_user_id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"Impersonation target user not found: {target_user_id}",
            )
        return User.model_validate(user)

    user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )
    return User.model_validate(user)


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
async def get_user(user_id: UUID, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )
    return User.model_validate(user)
