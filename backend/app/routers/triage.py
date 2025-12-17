from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.auth import RequireAuth
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
    current_user: RequireAuth,
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def create_connection(current_user: RequireAuth, connection: TriageConnectionCreate):
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def get_connection(connection_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")


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
    connection_id: UUID, current_user: RequireAuth, connection: TriageConnectionUpdate
):
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def delete_connection(connection_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/triage-connections/{connection_id}/sync",
    summary="Trigger manual sync",
    description="Trigger a manual sync from the external issue tracker.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Connection not found"},
    },
)
async def sync_connection(connection_id: UUID, current_user: RequireAuth):
    raise HTTPException(status_code=501, detail="Not implemented")


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
    current_user: RequireAuth,
    status: TriageItemStatus | None = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    raise HTTPException(status_code=501, detail="Not implemented")


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
    },
)
async def plan_from_item(item_id: UUID, current_user: RequireAuth, plan_request: TriageItemPlan):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/triage-items/{item_id}/reject",
    response_model=TriageItem,
    summary="Reject triage item",
    description="Reject a triage item as not suitable for ATC.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Item not found"},
    },
)
async def reject_item(
    item_id: UUID, current_user: RequireAuth, reject_request: TriageItemReject | None = None
):
    raise HTTPException(status_code=501, detail="Not implemented")
