from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from app.models.hat import HAT as HATModel
from app.models.project import ProjectSettings
from app.schemas import HAT, HATCreate, HATUpdate, PaginatedResponse

router = APIRouter()


@router.get("/hats", response_model=PaginatedResponse[HAT])
async def list_hats(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit

    items = db.scalars(select(HATModel).offset(offset).limit(limit)).all()
    total = db.scalar(select(func.count()).select_from(HATModel)) or 0
    pages = (total + limit - 1) // limit if total > 0 else 0

    return PaginatedResponse[HAT](
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post("/hats", response_model=HAT, status_code=status.HTTP_201_CREATED)
async def create_hat(hat: HATCreate, db: Session = Depends(get_db)):
    new_hat = HATModel(
        name=hat.name,
        description=hat.description,
        definition=hat.definition,
        enabled=hat.enabled,
    )
    db.add(new_hat)
    db.flush()
    return new_hat


@router.get("/hats/{hat_id}", response_model=HAT)
async def get_hat(hat_id: UUID, db: Session = Depends(get_db)):
    return get_or_404(db, HATModel, hat_id)


@router.patch("/hats/{hat_id}", response_model=HAT)
async def update_hat(hat_id: UUID, hat: HATUpdate, db: Session = Depends(get_db)):
    db_hat = get_or_404(db, HATModel, hat_id)

    update_data = hat.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_hat, key, value)

    db.flush()
    return db_hat


@router.delete("/hats/{hat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hat(hat_id: UUID, db: Session = Depends(get_db)):
    db_hat = get_or_404(db, HATModel, hat_id)

    project_settings_list = db.scalars(select(ProjectSettings)).all()
    for settings in project_settings_list:
        if hat_id in settings.assigned_hats:
            updated_hats = [h for h in settings.assigned_hats if h != hat_id]
            settings.assigned_hats = updated_hats

    db.delete(db_hat)
    db.flush()
