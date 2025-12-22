from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.plan import Plan as PlanModel
from app.models.project import Project as ProjectModel
from app.models.triage import TriageConnection as TriageConnectionModel
from app.models.triage import TriageItem as TriageItemModel
from app.schemas import (
    PaginatedResponse,
    Plan,
    TriageConnection,
    TriageConnectionCreate,
    TriageConnectionUpdate,
    TriageItem,
    TriageItemStatus,
)
from app.schemas.triage import TriageItemPlan, TriageItemReject

router = APIRouter()


@router.get("/triage-connections", response_model=PaginatedResponse[TriageConnection])
async def list_connections(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    connections = list(db.scalars(select(TriageConnectionModel)).all())

    total = len(connections)
    offset = (page - 1) * limit
    items = connections[offset : offset + limit]
    pages = (total + limit - 1) // limit if total > 0 else 0

    return PaginatedResponse[TriageConnection](
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post(
    "/triage-connections",
    response_model=TriageConnection,
    status_code=status.HTTP_201_CREATED,
)
async def create_connection(
    connection: TriageConnectionCreate, db: Session = Depends(get_db)
):
    new_connection = TriageConnectionModel(
        name=connection.name,
        provider=connection.provider,
        config=connection.config,
    )
    db.add(new_connection)
    db.flush()
    return new_connection


@router.get("/triage-connections/{connection_id}", response_model=TriageConnection)
async def get_connection(connection_id: UUID, db: Session = Depends(get_db)):
    connection = db.scalar(
        select(TriageConnectionModel).where(TriageConnectionModel.id == connection_id)
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    return connection


@router.patch("/triage-connections/{connection_id}", response_model=TriageConnection)
async def update_connection(
    connection_id: UUID,
    connection: TriageConnectionUpdate,
    db: Session = Depends(get_db),
):
    db_connection = db.scalar(
        select(TriageConnectionModel).where(TriageConnectionModel.id == connection_id)
    )
    if not db_connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    update_data = connection.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(db_connection, key, value)

    db.flush()
    return db_connection


@router.delete(
    "/triage-connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_connection(connection_id: UUID, db: Session = Depends(get_db)):
    db_connection = db.scalar(
        select(TriageConnectionModel).where(TriageConnectionModel.id == connection_id)
    )
    if not db_connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    db.delete(db_connection)
    db.flush()


@router.post("/triage-connections/{connection_id}/sync")
async def sync_connection(connection_id: UUID, db: Session = Depends(get_db)):
    connection = db.scalar(
        select(TriageConnectionModel).where(TriageConnectionModel.id == connection_id)
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    sync_id = uuid4()

    return {
        "sync_id": sync_id,
        "connection_id": connection_id,
        "message": "Sync initiated. Actual sync logic is not yet implemented.",
    }


@router.get(
    "/triage-connections/{connection_id}/items",
    response_model=PaginatedResponse[TriageItem],
)
async def list_connection_items(
    connection_id: UUID,
    status: TriageItemStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    connection = db.scalar(
        select(TriageConnectionModel).where(TriageConnectionModel.id == connection_id)
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    items = connection.items
    if status is not None:
        items = [item for item in items if item.status == status]

    total = len(items)
    offset = (page - 1) * limit
    paginated_items = items[offset : offset + limit]
    pages = (total + limit - 1) // limit if total > 0 else 0

    return PaginatedResponse[TriageItem](
        items=paginated_items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post(
    "/triage-items/{item_id}/plan",
    response_model=Plan,
    status_code=status.HTTP_201_CREATED,
)
async def plan_from_item(
    item_id: UUID, plan_request: TriageItemPlan, db: Session = Depends(get_db)
):
    triage_item = db.scalar(
        select(TriageItemModel).where(TriageItemModel.id == item_id)
    )
    if not triage_item:
        raise HTTPException(status_code=404, detail="Triage item not found")

    if triage_item.plan_id is not None:
        raise HTTPException(status_code=409, detail="Triage item already has a plan")

    project = db.scalar(
        select(ProjectModel).where(ProjectModel.id == plan_request.project_id)
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_plan = PlanModel(
        project_id=plan_request.project_id,
        title=triage_item.title,
        content=triage_item.description,
    )
    db.add(new_plan)
    db.flush()

    triage_item.plan_id = new_plan.id
    triage_item.status = TriageItemStatus.PLANNED

    db.flush()
    return new_plan


@router.post("/triage-items/{item_id}/reject", response_model=TriageItem)
async def reject_item(
    item_id: UUID,
    reject_request: TriageItemReject | None = None,
    db: Session = Depends(get_db),
):
    triage_item = db.scalar(
        select(TriageItemModel).where(TriageItemModel.id == item_id)
    )
    if not triage_item:
        raise HTTPException(status_code=404, detail="Triage item not found")

    if triage_item.status != TriageItemStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail=f"Triage item is already {triage_item.status.value}",
        )

    triage_item.status = TriageItemStatus.REJECTED

    db.flush()
    return triage_item
