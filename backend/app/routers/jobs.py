"""Job queue monitoring endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job_execution import JobExecution, JobStatus
from app.services.task_queue import cancel_job, get_job_status, get_queue_info

logger = logging.getLogger(__name__)

router = APIRouter()


class JobStatusResponse(BaseModel):
    """Response model for job status."""

    job_id: str
    status: str
    result: dict[str, Any] | None = None
    info: dict[str, Any] | None = None


class QueueHealthResponse(BaseModel):
    """Response model for queue health."""

    redis_connected: bool
    queued_job_count: int
    queued_jobs: list[dict[str, Any]]


class JobStatsResponse(BaseModel):
    """Response model for job statistics."""

    by_status: list[dict[str, Any]]


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status",
    description="Get the current status of a specific job from the queue.",
)
async def get_job_details(job_id: str):
    """Get details about a specific job."""
    try:
        status = await get_job_status(job_id)
        return JobStatusResponse(
            job_id=status["job_id"],
            status=status["status"],
            result=status.get("result"),
            info=status.get("info"),
        )
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {e}")


@router.delete(
    "/jobs/{job_id}",
    summary="Cancel job",
    description="Attempt to cancel a running or queued job.",
)
async def cancel_job_endpoint(job_id: str):
    """Cancel a job by ID."""
    try:
        cancelled = await cancel_job(job_id)
        if cancelled:
            return {"status": "cancelled", "job_id": job_id}
        else:
            return {"status": "not_cancelled", "job_id": job_id, "reason": "Job may have already completed or does not exist"}
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {e}")


@router.get(
    "/jobs",
    summary="List job executions",
    description="List job executions from the audit trail with optional filtering.",
)
async def list_jobs(
    status: JobStatus | None = Query(default=None, description="Filter by job status"),
    job_type: str | None = Query(default=None, description="Filter by job type"),
    limit: int = Query(default=50, le=100, description="Maximum number of jobs to return"),
    db: Session = Depends(get_db),
):
    """List job executions from the audit trail."""
    query = db.query(JobExecution)

    if status:
        query = query.filter(JobExecution.status == status)
    if job_type:
        query = query.filter(JobExecution.job_type == job_type)

    jobs = query.order_by(JobExecution.created_at.desc()).limit(limit).all()

    return [
        {
            "id": str(job.id),
            "job_id": job.job_id,
            "job_type": job.job_type,
            "target_id": str(job.target_id) if job.target_id else None,
            "target_type": job.target_type,
            "status": job.status.value,
            "attempt_number": job.attempt_number,
            "queued_at": job.queued_at.isoformat() if job.queued_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "duration_ms": job.duration_ms,
            "error_message": job.error_message,
            "worker_id": job.worker_id,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
        for job in jobs
    ]


@router.get(
    "/jobs/stats",
    response_model=JobStatsResponse,
    summary="Get job statistics",
    description="Get aggregated statistics about job executions.",
)
async def get_job_stats(db: Session = Depends(get_db)):
    """Get job execution statistics."""
    stats = (
        db.query(
            JobExecution.status,
            func.count(JobExecution.id).label("count"),
            func.avg(JobExecution.duration_ms).label("avg_duration_ms"),
        )
        .group_by(JobExecution.status)
        .all()
    )

    return JobStatsResponse(
        by_status=[
            {
                "status": s.status.value,
                "count": s.count,
                "avg_duration_ms": float(s.avg_duration_ms) if s.avg_duration_ms else None,
            }
            for s in stats
        ]
    )


@router.get(
    "/queue/health",
    response_model=QueueHealthResponse,
    summary="Get queue health",
    description="Get Redis queue health information.",
)
async def get_queue_health():
    """Get Redis queue health information."""
    try:
        info = await get_queue_info()
        return QueueHealthResponse(
            redis_connected=info["redis_connected"],
            queued_job_count=info["queued_job_count"],
            queued_jobs=info["queued_jobs"],
        )
    except Exception as e:
        logger.error(f"Error getting queue health: {e}")
        return QueueHealthResponse(
            redis_connected=False,
            queued_job_count=0,
            queued_jobs=[],
        )
