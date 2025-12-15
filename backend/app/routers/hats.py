from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas import HAT, HATCreate, HATType, HATUpdate, PaginatedResponse, StandardError

router = APIRouter()


@router.get(
    "/hats",
    response_model=PaginatedResponse[HAT],
    summary="List HATs",
    description="Retrieve a paginated list of all HATs with optional type filtering.",
    responses={401: {"model": StandardError, "description": "Unauthorized"}},
)
async def list_hats(
    type: HATType | None = Query(default=None, description="Filter by HAT type"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    """List all HATs with pagination."""
    # TODO: Implement database query
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def create_hat(hat: HATCreate):
    """Create a new HAT."""
    # TODO: Implement database insert
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def get_hat(hat_id: UUID):
    """Get HAT by ID."""
    # TODO: Implement database query
    raise HTTPException(status_code=501, detail="Not implemented")


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
async def update_hat(hat_id: UUID, hat: HATUpdate):
    """Update a HAT."""
    # TODO: Implement database update
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete(
    "/hats/{hat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete HAT",
    description="Delete a HAT.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "HAT not found"},
    },
)
async def delete_hat(hat_id: UUID):
    """Delete a HAT."""
    # TODO: Implement database delete
    raise HTTPException(status_code=501, detail="Not implemented")
