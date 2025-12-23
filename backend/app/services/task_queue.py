"""Background task queue for async operations.

This module provides a simple in-memory task queue for background processing.
In production, this should be replaced with a proper task queue like Celery, ARQ, or Dramatiq.

See ticket: 54156901-6298-4b71-9f93-c74cdf2f0495
"""

import asyncio
import logging
from typing import Callable, Coroutine, Any
from uuid import UUID

logger = logging.getLogger(__name__)

# In-memory task storage
# TODO: Replace with proper task queue (Celery, ARQ, Dramatiq)
# See ticket: 54156901-6298-4b71-9f93-c74cdf2f0495
_tasks: dict[UUID, asyncio.Task] = {}


def submit_task(task_id: UUID, coro: Coroutine[Any, Any, None]) -> asyncio.Task:
    """Submit a coroutine to run as a background task.

    Args:
        task_id: Unique identifier for the task
        coro: Coroutine to execute

    Returns:
        The created asyncio.Task

    Raises:
        ValueError: If a task with the same ID is already running
    """
    if task_id in _tasks and not _tasks[task_id].done():
        raise ValueError(f"Task {task_id} is already running")

    async def _wrapped_task():
        try:
            await coro
        finally:
            # Clean up task reference when done
            _tasks.pop(task_id, None)

    task = asyncio.create_task(_wrapped_task())
    _tasks[task_id] = task
    logger.debug(f"Submitted background task {task_id}")
    return task


def is_task_running(task_id: UUID) -> bool:
    """Check if a task is currently running.

    Args:
        task_id: Task identifier to check

    Returns:
        True if task exists and is not done, False otherwise
    """
    return task_id in _tasks and not _tasks[task_id].done()


def get_task(task_id: UUID) -> asyncio.Task | None:
    """Get a task by ID.

    Args:
        task_id: Task identifier

    Returns:
        The asyncio.Task if it exists, None otherwise
    """
    return _tasks.get(task_id)


def cancel_task(task_id: UUID) -> bool:
    """Cancel a running task.

    Args:
        task_id: Task identifier to cancel

    Returns:
        True if task was cancelled, False if task not found or already done
    """
    task = _tasks.get(task_id)
    if task and not task.done():
        task.cancel()
        _tasks.pop(task_id, None)
        logger.info(f"Cancelled background task {task_id}")
        return True
    return False


def get_running_task_count() -> int:
    """Get the number of currently running tasks.

    Returns:
        Count of running tasks
    """
    # Clean up completed tasks while counting
    completed = [tid for tid, task in _tasks.items() if task.done()]
    for tid in completed:
        _tasks.pop(tid, None)
    return len(_tasks)
