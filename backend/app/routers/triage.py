from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.plan import Plan as PlanModel
from app.models.project import Project as ProjectModel
from app.models.triage import TriageConnection as TriageConnectionModel
from app.models.triage import TriageItem as TriageItemModel
from app.schemas import (
    PaginatedResponse,
    Plan,
    StandardError,
    TriageConnection,
    TriageConnectionCreate,
    TriageConnectionUpdate,
    TriageItem,
    TriageItemStatus,
)
from app.schemas.triage import TriageItemPlan, TriageItemReject

router = APIRouter()


@router.get(
    "/triage-connections",
    response_model=PaginatedResponse[TriageConnection],
    summary="List triage connections",
    description="Retrieve a paginated list of all triage connections.",
    responses={401: {"model": StandardError, "description": "Unauthorized"}},
)
async def list_connections(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_session),
):
    connections = list(session.scalars(select(TriageConnectionModel)).all())

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
    summary="Create triage connection",
    description="Create a new connection to an external issue tracker.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
    },
)
async def create_connection(
    connection: TriageConnectionCreate, session: Session = Depends(get_session)
):
    new_connection = TriageConnectionModel(
        name=connection.name,
        provider=connection.provider.value,
        config=connection.config,
    )
    session.add(new_connection)
    session.flush()
    return new_connection


@router.get(
    "/triage-connections/{connection_id}",
    response_model=TriageConnection,
    summary="Get connection details",
    description="Retrieve details of a specific triage connection.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Connection not found"},
    },
)
async def get_connection(connection_id: UUID, session: Session = Depends(get_session)):
    connection = TriageConnectionModel.get_or_404(session, connection_id)
    return connection


@router.patch(
    "/triage-connections/{connection_id}",
    response_model=TriageConnection,
    summary="Update connection",
    description="Update a triage connection's configuration.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Connection not found"},
    },
)
async def update_connection(
    connection_id: UUID,
    connection: TriageConnectionUpdate,
    session: Session = Depends(get_session),
):
    db_connection = TriageConnectionModel.get_or_404(session, connection_id)

    update_data = connection.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(db_connection, key, value)

    session.flush()
    return db_connection


@router.delete(
    "/triage-connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete connection",
    description="Delete a triage connection.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Connection not found"},
    },
)
async def delete_connection(connection_id: UUID, session: Session = Depends(get_session)):
    db_connection = TriageConnectionModel.get_or_404(session, connection_id)
    session.delete(db_connection)
    session.flush()


@router.post(
    "/triage-connections/{connection_id}/sync",
    summary="Trigger manual sync",
    description="Trigger a manual sync from the external issue tracker.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Connection not found"},
    },
)
async def sync_connection(connection_id: UUID, session: Session = Depends(get_session)):
    # Validate connection exists
    TriageConnectionModel.get_or_404(session, connection_id)

    # Generate a sync_id for tracking (actual sync logic deferred)
    sync_id = uuid4()

    return {
        "sync_id": sync_id,
        "connection_id": connection_id,
        "message": "Sync initiated. Actual sync logic is not yet implemented.",
    }


@router.get(
    "/triage-connections/{connection_id}/items",
    response_model=PaginatedResponse[TriageItem],
    summary="List triage items",
    description="List imported issues from a triage connection with optional status filtering.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Connection not found"},
    },
)
async def list_connection_items(
    connection_id: UUID,
    status: TriageItemStatus | None = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_session),
):
    connection = TriageConnectionModel.get_or_404(session, connection_id)

    items = connection.items
    if status is not None:
        items = [item for item in items if item.status == status.value]

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
    summary="Create plan from triage item",
    description="Create a new plan from a triage item. Requires project_id.",
    responses={
        400: {"model": StandardError, "description": "Validation error"},
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Item not found"},
        409: {"model": StandardError, "description": "Item already has a plan"},
    },
)
async def plan_from_item(
    item_id: UUID, plan_request: TriageItemPlan, session: Session = Depends(get_session)
):
    # Get the triage item
    triage_item = TriageItemModel.get_or_404(session, item_id)

    # Check if item already has a plan
    if triage_item.plan_id is not None:
        raise HTTPException(status_code=409, detail="Triage item already has a plan")

    # Validate project exists
    ProjectModel.get_or_404(session, plan_request.project_id)

    # Create the plan from the triage item data
    new_plan = PlanModel(
        project_id=plan_request.project_id,
        title=triage_item.title,
        content=triage_item.description,
    )
    session.add(new_plan)
    session.flush()

    # Link the triage item to the plan and update status
    triage_item.plan_id = new_plan.id
    triage_item.status = TriageItemStatus.PLANNED.value

    session.flush()
    return new_plan


@router.post(
    "/triage-items/{item_id}/reject",
    response_model=TriageItem,
    summary="Reject triage item",
    description="Reject a triage item as not suitable for ATC.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Item not found"},
        409: {"model": StandardError, "description": "Item already planned or rejected"},
    },
)
async def reject_item(
    item_id: UUID,
    reject_request: TriageItemReject | None = None,
    session: Session = Depends(get_session),
):
    triage_item = TriageItemModel.get_or_404(session, item_id)

    # Check if item is already planned or rejected
    if triage_item.status != TriageItemStatus.PENDING.value:
        raise HTTPException(
            status_code=409,
            detail=f"Triage item is already {triage_item.status}",
        )

    # Update status to rejected
    triage_item.status = TriageItemStatus.REJECTED.value

    # Note: The rejection reason is accepted but not stored in the current model
    # If needed, add a 'rejection_reason' field to the TriageItem model

    session.flush()
    return triage_item
