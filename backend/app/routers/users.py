from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User as UserModel
from app.schemas import PaginatedResponse, User

router = APIRouter()


def _get_user_id_from_request(request: Request) -> UUID:
    impersonate_header = request.headers.get("X-Impersonate-User")
    if impersonate_header:
        try:
            return UUID(impersonate_header)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid X-Impersonate-User UUID")
    return get_current_user(request).id


@router.get("/users", response_model=PaginatedResponse[User])
async def list_users(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit

    items = db.scalars(select(UserModel).offset(offset).limit(limit)).all()
    total = db.scalar(select(func.count()).select_from(UserModel)) or 0
    pages = (total + limit - 1) // limit if total > 0 else 0

    return PaginatedResponse[User](
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/users/me", response_model=User)
async def get_current_user_endpoint(
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = _get_user_id_from_request(request)
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User.model_validate(user)


@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: UUID, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User.model_validate(user)
