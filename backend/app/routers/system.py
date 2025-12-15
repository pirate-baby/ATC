from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas import StandardError

router = APIRouter()


class SystemStats(BaseModel):
    active_sessions: int = Field(description="Number of currently running coding sessions")
    pending_reviews: int = Field(description="Number of items awaiting review")
    tasks_in_progress: int = Field(description="Number of tasks currently being worked on")
    total_projects: int = Field(description="Total number of projects")
    total_plans: int = Field(description="Total number of plans")
    total_tasks: int = Field(description="Total number of tasks")


@router.get(
    "/system/stats",
    response_model=SystemStats,
    summary="Get system statistics",
    description="Retrieve system-wide statistics including active sessions and pending reviews.",
    responses={401: {"model": StandardError, "description": "Unauthorized"}},
)
async def get_system_stats():
    raise HTTPException(status_code=501, detail="Not implemented")
