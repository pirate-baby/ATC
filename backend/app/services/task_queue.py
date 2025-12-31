"""Background task queue using ARQ with Redis.

Provides crash-resilient task execution with retry logic,
persistence, and monitoring capabilities.
"""

import logging
from typing import Any
from uuid import UUID, uuid4

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from arq.jobs import Job, JobStatus as ArqJobStatus

from app.config import settings

logger = logging.getLogger(__name__)

# Global connection pool (initialized on startup)
_redis_pool: ArqRedis | None = None


def get_redis_settings() -> RedisSettings:
    """Get Redis settings from application config."""
    return RedisSettings.from_dsn(settings.redis_url)


async def get_redis_pool() -> ArqRedis:
    """Get or create the Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await create_pool(get_redis_settings())
    return _redis_pool


async def close_redis_pool() -> None:
    """Close the Redis connection pool."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None


# ============================================================================
# Job Definitions (executed by workers)
# ============================================================================


async def run_plan_generation(
    ctx: dict[str, Any],
    plan_id: str,
    title: str,
    context: str | None,
    project_context: str | None,
) -> dict[str, Any]:
    """Generate plan content using Claude.

    This job is executed by ARQ workers with automatic retry on failure.
    """
    logger.info(f"Starting plan generation job for plan_id={plan_id}, title='{title}'")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.enums import ProcessingStatus
    from app.models.plan import Plan as PlanModel
    from app.services.claude import (
        ClaudeGenerationError,
        ClaudeNotConfiguredError,
        claude_service,
    )

    plan_uuid = UUID(plan_id)

    # Create database session for this job
    logger.debug(f"Creating database session for plan generation job {plan_id}")
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = SessionLocal()

    try:
        plan = db.query(PlanModel).filter(PlanModel.id == plan_uuid).first()
        if not plan:
            logger.error(f"Plan {plan_id} not found during generation")
            return {"success": False, "error": "Plan not found"}

        logger.info(f"Calling Claude service to generate plan content for plan_id={plan_id}")

        try:
            result = await claude_service.generate_plan(
                plan_id=plan_uuid,
                title=title,
                context=context,
                project_context=project_context,
            )

            plan.content = result.content
            plan.processing_status = ProcessingStatus.COMPLETED
            plan.processing_error = None
            db.commit()

            logger.info(
                f"Plan generation completed successfully for plan_id={plan_id}, "
                f"content_length={len(result.content)}"
            )
            return {
                "success": True,
                "plan_id": plan_id,
                "content_length": len(result.content),
            }

        except (ClaudeNotConfiguredError, ClaudeGenerationError) as e:
            logger.error(
                f"Plan generation failed for plan_id={plan_id}: {e!r}",
                exc_info=True,
            )
            plan.processing_status = ProcessingStatus.FAILED
            plan.processing_error = str(e)
            db.commit()
            raise  # Re-raise to trigger ARQ retry

    except Exception as e:
        logger.error(
            f"Unexpected error during plan generation for plan_id={plan_id}: {e!r}",
            exc_info=True,
        )
        try:
            plan = db.query(PlanModel).filter(PlanModel.id == plan_uuid).first()
            if plan:
                plan.processing_status = ProcessingStatus.FAILED
                plan.processing_error = f"Unexpected error: {e}"
                db.commit()
        except Exception as inner_e:
            logger.error(
                f"Failed to update plan status after error for plan_id={plan_id}: {inner_e!r}",
                exc_info=True,
            )
        raise

    finally:
        db.close()
        engine.dispose()


async def run_task_spawning(
    ctx: dict[str, Any],
    plan_id: str,
    title: str,
    content: str,
    project_id: str,
    project_context: str | None,
) -> dict[str, Any]:
    """Generate tasks from approved plan using Claude.

    This job is executed by ARQ workers with automatic retry on failure.
    """
    logger.info(f"Starting task spawning job for plan_id={plan_id}, title='{title}'")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.enums import PlanTaskStatus as ModelPlanTaskStatus
    from app.models.enums import ProcessingStatus
    from app.models.plan import Plan as PlanModel
    from app.models.task import Task as TaskModel
    from app.services.claude import (
        ClaudeGenerationError,
        ClaudeNotConfiguredError,
        claude_service,
    )

    plan_uuid = UUID(plan_id)
    project_uuid = UUID(project_id)

    logger.debug(f"Creating database session for task spawning job {plan_id}")
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = SessionLocal()

    try:
        plan = db.query(PlanModel).filter(PlanModel.id == plan_uuid).first()
        if not plan:
            logger.error(f"Plan {plan_id} not found during task spawning")
            return {"success": False, "error": "Plan not found"}

        logger.info(f"Calling Claude service to generate tasks for plan_id={plan_id}")

        try:
            result = await claude_service.generate_tasks(
                plan_id=plan_uuid,
                title=title,
                content=content,
                project_context=project_context,
            )

            logger.info(f"Claude returned {len(result.tasks)} tasks for plan_id={plan_id}")

            created_tasks: list[TaskModel] = []
            for i, generated_task in enumerate(result.tasks):
                logger.debug(f"Creating task {i+1}/{len(result.tasks)}: '{generated_task.title}'")
                new_task = TaskModel(
                    project_id=project_uuid,
                    plan_id=plan_uuid,
                    title=generated_task.title,
                    description=generated_task.description,
                )
                db.add(new_task)
                db.flush()
                created_tasks.append(new_task)

            # Set up blocking relationships
            logger.debug(f"Setting up blocking relationships for {len(created_tasks)} tasks")
            for i, generated_task in enumerate(result.tasks):
                if generated_task.blocked_by_indices:
                    blocking_tasks = [
                        created_tasks[idx]
                        for idx in generated_task.blocked_by_indices
                        if idx < len(created_tasks)
                    ]
                    created_tasks[i].blocked_by = blocking_tasks
                    if blocking_tasks:
                        created_tasks[i].status = ModelPlanTaskStatus.BLOCKED
                        logger.debug(
                            f"Task '{created_tasks[i].title}' blocked by {len(blocking_tasks)} tasks"
                        )

            plan.processing_status = ProcessingStatus.COMPLETED
            plan.processing_error = None
            db.commit()

            logger.info(
                f"Task spawning completed successfully for plan_id={plan_id}, "
                f"created {len(created_tasks)} tasks"
            )
            return {
                "success": True,
                "plan_id": plan_id,
                "tasks_created": len(created_tasks),
            }

        except (ClaudeNotConfiguredError, ClaudeGenerationError) as e:
            logger.error(
                f"Task spawning failed for plan_id={plan_id}: {e!r}",
                exc_info=True,
            )
            plan.processing_status = ProcessingStatus.FAILED
            plan.processing_error = str(e)
            db.commit()
            raise

    except Exception as e:
        logger.error(
            f"Unexpected error during task spawning for plan_id={plan_id}: {e!r}",
            exc_info=True,
        )
        try:
            plan = db.query(PlanModel).filter(PlanModel.id == plan_uuid).first()
            if plan:
                plan.processing_status = ProcessingStatus.FAILED
                plan.processing_error = f"Unexpected error: {e}"
                db.commit()
        except Exception as inner_e:
            logger.error(
                f"Failed to update plan status after error for plan_id={plan_id}: {inner_e!r}",
                exc_info=True,
            )
        raise

    finally:
        db.close()
        engine.dispose()


# ============================================================================
# Task Submission API (used by FastAPI endpoints)
# ============================================================================


async def submit_plan_generation(
    plan_id: UUID,
    title: str,
    context: str | None = None,
    project_context: str | None = None,
) -> str:
    """Submit a plan generation job to the queue.

    Returns the ARQ job ID for status tracking.
    """
    pool = await get_redis_pool()
    job_id = f"plan_gen_{plan_id}"

    # First, try to abort any existing job with this ID (in case of retry)
    existing_job = Job(job_id, pool)
    existing_status = await existing_job.status()
    if existing_status is not None:
        logger.info(f"Found existing job {job_id} with status {existing_status}, aborting it")
        await existing_job.abort()

    job = await pool.enqueue_job(
        "run_plan_generation",
        str(plan_id),
        title,
        context,
        project_context,
        _job_id=job_id,
    )

    if job is None:
        # Job with this ID already exists and couldn't be replaced
        logger.warning(f"Job {job_id} already exists, returning existing job ID")
        return job_id

    logger.info(f"Submitted plan generation job for plan_id={plan_id}, job_id={job.job_id}")
    return job.job_id


async def submit_task_spawning(
    plan_id: UUID,
    title: str,
    content: str,
    project_id: UUID,
    project_context: str | None = None,
) -> str:
    """Submit a task spawning job to the queue.

    Returns the ARQ job ID for status tracking.
    """
    pool = await get_redis_pool()
    job_id = f"task_spawn_{plan_id}"

    # First, try to abort any existing job with this ID (in case of retry)
    existing_job = Job(job_id, pool)
    existing_status = await existing_job.status()
    if existing_status is not None:
        logger.info(f"Found existing job {job_id} with status {existing_status}, aborting it")
        await existing_job.abort()

    job = await pool.enqueue_job(
        "run_task_spawning",
        str(plan_id),
        title,
        content,
        str(project_id),
        project_context,
        _job_id=job_id,
    )

    if job is None:
        # Job with this ID already exists and couldn't be replaced
        logger.warning(f"Job {job_id} already exists, returning existing job ID")
        return job_id

    logger.info(f"Submitted task spawning job for plan_id={plan_id}, job_id={job.job_id}")
    return job.job_id


async def get_job_status(job_id: str) -> dict[str, Any]:
    """Get the status of a job by ID."""
    pool = await get_redis_pool()
    job = Job(job_id, pool)
    status = await job.status()
    info = await job.info()

    result = None
    if status == ArqJobStatus.complete:
        try:
            result = await job.result()
        except Exception as e:
            logger.error(f"Failed to get result for completed job {job_id}: {e!r}", exc_info=True)

    return {
        "job_id": job_id,
        "status": status.value if status else "unknown",
        "result": result,
        "info": info,
    }


async def is_job_running(job_id: str) -> bool:
    """Check if a job is currently running or queued."""
    pool = await get_redis_pool()
    job = Job(job_id, pool)
    status = await job.status()
    return status in (ArqJobStatus.queued, ArqJobStatus.in_progress)


async def cancel_job(job_id: str) -> bool:
    """Attempt to cancel a job."""
    pool = await get_redis_pool()
    job = Job(job_id, pool)
    return await job.abort()


async def get_queue_info() -> dict[str, Any]:
    """Get information about the queue status."""
    pool = await get_redis_pool()
    queued_jobs = await pool.queued_jobs()

    return {
        "redis_connected": True,
        "queued_job_count": len(queued_jobs) if queued_jobs else 0,
        "queued_jobs": [
            {"job_id": job.job_id, "function": job.function, "enqueue_time": job.enqueue_time}
            for job in (queued_jobs or [])[:10]  # Limit to first 10
        ],
    }


# ============================================================================
# ARQ Worker Configuration
# ============================================================================


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup hook."""
    ctx["worker_id"] = str(uuid4())[:8]
    logger.info(f"ARQ worker starting up with id={ctx['worker_id']}")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown hook."""
    logger.info(f"ARQ worker shutting down with id={ctx.get('worker_id')}")


async def on_job_start(ctx: dict[str, Any]) -> None:
    """Called when a job starts."""
    job_name = ctx.get('job_name', 'unknown')
    job_id = ctx.get('job_id', 'unknown')
    worker_id = ctx.get('worker_id', 'unknown')
    logger.info(f"Job '{job_name}' starting: {job_id} on worker {worker_id}")


async def on_job_end(ctx: dict[str, Any]) -> None:
    """Called when a job ends (success or failure)."""
    job_name = ctx.get('job_name', 'unknown')
    job_id = ctx.get('job_id', 'unknown')
    job_try = ctx.get('job_try', 0)
    logger.info(f"Job '{job_name}' ended: {job_id} (attempt {job_try})")


class WorkerSettings:
    """ARQ Worker configuration."""

    functions = [
        run_plan_generation,
        run_task_spawning,
    ]

    redis_settings = get_redis_settings()

    # Retry configuration with exponential backoff
    max_tries = settings.task_queue_max_retries
    retry_jobs = True

    # Job timeout (for long-running Claude API calls)
    job_timeout = settings.task_queue_job_timeout_seconds

    # Concurrency (adjust based on Claude API rate limits)
    max_jobs = 10

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown
    after_job_end = on_job_end

    # Health check
    health_check_interval = 30

    # Keep results for 24 hours
    keep_result = 86400
