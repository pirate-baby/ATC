"""Tests for ARQ-based task queue service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from arq.jobs import JobStatus as ArqJobStatus


class TestSubmitPlanGeneration:
    """Tests for submit_plan_generation function."""

    @pytest.mark.asyncio
    async def test_submit_returns_job_id(self, mock_redis_pool):
        """Test that submitting a plan generation job returns the job ID."""
        from app.services.task_queue import submit_plan_generation

        plan_id = uuid4()
        job_id = await submit_plan_generation(
            plan_id=plan_id,
            title="Test Plan",
            context="Test context",
            project_context="Project: Test",
        )

        assert job_id == "test_job_123"
        mock_redis_pool.enqueue_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_uses_correct_job_id_format(self, mock_redis_pool):
        """Test that the job ID follows the expected format."""
        from app.services.task_queue import submit_plan_generation

        plan_id = uuid4()
        await submit_plan_generation(
            plan_id=plan_id,
            title="Test Plan",
        )

        # Check that enqueue_job was called with the correct job_id kwarg
        call_kwargs = mock_redis_pool.enqueue_job.call_args
        assert call_kwargs.kwargs["_job_id"] == f"plan_gen_{plan_id}"


class TestSubmitTaskSpawning:
    """Tests for submit_task_spawning function."""

    @pytest.mark.asyncio
    async def test_submit_returns_job_id(self, mock_redis_pool):
        """Test that submitting a task spawning job returns the job ID."""
        from app.services.task_queue import submit_task_spawning

        plan_id = uuid4()
        project_id = uuid4()

        job_id = await submit_task_spawning(
            plan_id=plan_id,
            title="Test Plan",
            content="Plan content",
            project_id=project_id,
            project_context="Project: Test",
        )

        assert job_id == "test_job_123"
        mock_redis_pool.enqueue_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_uses_correct_job_id_format(self, mock_redis_pool):
        """Test that the job ID follows the expected format."""
        from app.services.task_queue import submit_task_spawning

        plan_id = uuid4()
        project_id = uuid4()

        await submit_task_spawning(
            plan_id=plan_id,
            title="Test Plan",
            content="Plan content",
            project_id=project_id,
        )

        call_kwargs = mock_redis_pool.enqueue_job.call_args
        assert call_kwargs.kwargs["_job_id"] == f"task_spawn_{plan_id}"


class TestIsJobRunning:
    """Tests for is_job_running function."""

    @pytest.mark.asyncio
    async def test_returns_true_when_queued(self):
        """Test that is_job_running returns True for queued jobs."""
        from app.services.task_queue import is_job_running

        mock_job = AsyncMock()
        mock_job.status = AsyncMock(return_value=ArqJobStatus.queued)

        mock_pool = AsyncMock()

        with patch("app.services.task_queue.get_redis_pool", AsyncMock(return_value=mock_pool)):
            with patch("app.services.task_queue.Job", return_value=mock_job):
                result = await is_job_running("test_job")
                assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_when_in_progress(self):
        """Test that is_job_running returns True for in-progress jobs."""
        from app.services.task_queue import is_job_running

        mock_job = AsyncMock()
        mock_job.status = AsyncMock(return_value=ArqJobStatus.in_progress)

        mock_pool = AsyncMock()

        with patch("app.services.task_queue.get_redis_pool", AsyncMock(return_value=mock_pool)):
            with patch("app.services.task_queue.Job", return_value=mock_job):
                result = await is_job_running("test_job")
                assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_complete(self):
        """Test that is_job_running returns False for completed jobs."""
        from app.services.task_queue import is_job_running

        mock_job = AsyncMock()
        mock_job.status = AsyncMock(return_value=ArqJobStatus.complete)

        mock_pool = AsyncMock()

        with patch("app.services.task_queue.get_redis_pool", AsyncMock(return_value=mock_pool)):
            with patch("app.services.task_queue.Job", return_value=mock_job):
                result = await is_job_running("test_job")
                assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self):
        """Test that is_job_running returns False for non-existent jobs."""
        from app.services.task_queue import is_job_running

        mock_job = AsyncMock()
        mock_job.status = AsyncMock(return_value=None)

        mock_pool = AsyncMock()

        with patch("app.services.task_queue.get_redis_pool", AsyncMock(return_value=mock_pool)):
            with patch("app.services.task_queue.Job", return_value=mock_job):
                result = await is_job_running("test_job")
                assert result is False


class TestGetJobStatus:
    """Tests for get_job_status function."""

    @pytest.mark.asyncio
    async def test_returns_status_info(self):
        """Test that get_job_status returns expected fields."""
        from app.services.task_queue import get_job_status

        mock_job = AsyncMock()
        mock_job.status = AsyncMock(return_value=ArqJobStatus.complete)
        mock_job.info = AsyncMock(return_value={"function": "run_plan_generation"})
        mock_job.result = AsyncMock(return_value={"success": True})

        mock_pool = AsyncMock()

        with patch("app.services.task_queue.get_redis_pool", AsyncMock(return_value=mock_pool)):
            with patch("app.services.task_queue.Job", return_value=mock_job):
                result = await get_job_status("test_job")

                assert result["job_id"] == "test_job"
                assert result["status"] == "complete"
                assert result["result"] == {"success": True}


class TestGetQueueInfo:
    """Tests for get_queue_info function."""

    @pytest.mark.asyncio
    async def test_returns_queue_info(self, mock_redis_pool):
        """Test that get_queue_info returns expected structure."""
        from app.services.task_queue import get_queue_info

        result = await get_queue_info()

        assert result["redis_connected"] is True
        assert result["queued_job_count"] == 0
        assert result["queued_jobs"] == []


class TestWorkerSettings:
    """Tests for WorkerSettings configuration."""

    def test_worker_settings_has_required_functions(self):
        """Test that WorkerSettings has the required job functions."""
        from app.services.task_queue import WorkerSettings

        function_names = [f.__name__ for f in WorkerSettings.functions]
        assert "run_plan_generation" in function_names
        assert "run_task_spawning" in function_names

    def test_worker_settings_has_retry_config(self):
        """Test that WorkerSettings has retry configuration."""
        from app.services.task_queue import WorkerSettings

        assert WorkerSettings.max_tries >= 1
        assert WorkerSettings.retry_jobs is True

    def test_worker_settings_has_timeout(self):
        """Test that WorkerSettings has job timeout configured."""
        from app.services.task_queue import WorkerSettings

        # Should be at least 60 seconds for Claude API calls
        assert WorkerSettings.job_timeout >= 60

    def test_worker_settings_has_lifecycle_hooks(self):
        """Test that WorkerSettings has lifecycle hooks."""
        from app.services.task_queue import WorkerSettings

        assert WorkerSettings.on_startup is not None
        assert WorkerSettings.on_shutdown is not None
