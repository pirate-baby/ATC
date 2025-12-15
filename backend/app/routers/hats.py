from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.hat import HAT as HATModel
from app.models.project import ProjectSettings
from app.schemas import HAT, HATCreate, HATUpdate, PaginatedResponse, StandardError

router = APIRouter()


@router.get(
    "/hats",
    response_model=PaginatedResponse[HAT],
    summary="List HATs",
    description="Retrieve a paginated list of all HATs.",
    responses={401: {"model": StandardError, "description": "Unauthorized"}},
)
async def list_hats(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_session),
):
    offset = (page - 1) * limit

    items = session.scalars(select(HATModel).offset(offset).limit(limit)).all()
    total = session.scalar(select(func.count()).select_from(HATModel)) or 0
    pages = (total + limit - 1) // limit if total > 0 else 0

    return PaginatedResponse[HAT](
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post(
    "/hats",
    response_model=HAT,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new HAT",
    description="Create a new Heightened Ability Template.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
    },
)
async def create_hat(hat: HATCreate, session: Session = Depends(get_session)):
    new_hat = HATModel(
        name=hat.name,
        description=hat.description,
        definition=hat.definition,
        enabled=hat.enabled,
    )
    session.add(new_hat)
    session.flush()
    return new_hat


@router.get(
    "/hats/{hat_id}",
    response_model=HAT,
    summary="Get HAT by ID",
    description="Retrieve a specific HAT by its unique identifier.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "HAT not found"},
    },
)
async def get_hat(hat_id: UUID, session: Session = Depends(get_session)):
    return HATModel.get_or_404(session, hat_id)


@router.patch(
    "/hats/{hat_id}",
    response_model=HAT,
    summary="Update HAT",
    description="Update an existing HAT.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "HAT not found"},
    },
)
async def update_hat(hat_id: UUID, hat: HATUpdate, session: Session = Depends(get_session)):
    db_hat = HATModel.get_or_404(session, hat_id)

    update_data = hat.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_hat, key, value)

    session.flush()
    return db_hat


@router.delete(
    "/hats/{hat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete HAT",
    description="Delete a HAT. Also removes the HAT from all project assignments.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "HAT not found"},
    },
)
async def delete_hat(hat_id: UUID, session: Session = Depends(get_session)):
    db_hat = HATModel.get_or_404(session, hat_id)

    project_settings_list = session.scalars(select(ProjectSettings)).all()
    for settings in project_settings_list:
        if hat_id in settings.assigned_hats:
            updated_hats = [h for h in settings.assigned_hats if h != hat_id]
            settings.assigned_hats = updated_hats

    session.delete(db_hat)
    session.flush()
