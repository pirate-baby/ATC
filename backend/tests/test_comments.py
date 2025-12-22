"""Tests for comment system endpoints."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Plan, Project, Task, User
from app.models.comment import Comment as CommentModel
from app.models.comment import CommentThread as CommentThreadModel
from app.models.enums import CommentThreadStatus, CommentThreadTargetType


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def comment_thread_on_plan(session: Session, plan: Plan, user: User) -> CommentThreadModel:
    """Create a comment thread on a plan with an initial comment."""
    thread = CommentThreadModel(
        target_type=CommentThreadTargetType.PLAN,
        target_id=plan.id,
    )
    session.add(thread)
    session.flush()

    comment = CommentModel(
        thread_id=thread.id,
        author_id=user.id,
        content="Initial comment on plan",
    )
    session.add(comment)
    session.flush()
    return thread


@pytest.fixture
def comment_thread_on_task(session: Session, task: Task, user: User) -> CommentThreadModel:
    """Create a comment thread on a task with an initial comment."""
    thread = CommentThreadModel(
        target_type=CommentThreadTargetType.TASK,
        target_id=task.id,
    )
    session.add(thread)
    session.flush()

    comment = CommentModel(
        thread_id=thread.id,
        author_id=user.id,
        content="Initial comment on task",
    )
    session.add(comment)
    session.flush()
    return thread


@pytest.fixture
def comment_thread_on_code_line(session: Session, task: Task, user: User) -> CommentThreadModel:
    """Create a comment thread on a code line with an initial comment."""
    thread = CommentThreadModel(
        target_type=CommentThreadTargetType.LINE,
        target_id=task.id,
        file_path="src/main.py",
        line_number=42,
    )
    session.add(thread)
    session.flush()

    comment = CommentModel(
        thread_id=thread.id,
        author_id=user.id,
        content="Comment on code line",
    )
    session.add(comment)
    session.flush()
    return thread


# ============================================================================
# Plan Thread Endpoints
# ============================================================================


class TestListPlanThreads:
    def test_list_threads_empty(self, authed_client: TestClient, plan: Plan):
        response = authed_client.get(f"/api/v1/plans/{plan.id}/threads")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_threads_with_threads(
        self, authed_client: TestClient, plan: Plan, comment_thread_on_plan: CommentThreadModel
    ):
        response = authed_client.get(f"/api/v1/plans/{plan.id}/threads")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(comment_thread_on_plan.id)
        assert data[0]["target_type"] == "plan"
        assert data[0]["status"] == "open"

    def test_list_threads_plan_not_found(self, authed_client: TestClient):
        response = authed_client.get(f"/api/v1/plans/{uuid4()}/threads")
        assert response.status_code == 404


class TestCreatePlanThread:
    def test_create_thread(self, authed_client: TestClient, plan: Plan):
        response = authed_client.post(
            f"/api/v1/plans/{plan.id}/threads",
            json={
                "target_type": "plan",
                "initial_comment": "This is a new thread",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["target_type"] == "plan"
        assert data["target_id"] == str(plan.id)
        assert data["status"] == "open"

    def test_create_thread_wrong_target_type(self, authed_client: TestClient, plan: Plan):
        response = authed_client.post(
            f"/api/v1/plans/{plan.id}/threads",
            json={
                "target_type": "task",
                "initial_comment": "This should fail",
            },
        )
        assert response.status_code == 400
        assert "target_type must be 'plan'" in response.json()["detail"]

    def test_create_thread_plan_not_found(self, authed_client: TestClient):
        response = authed_client.post(
            f"/api/v1/plans/{uuid4()}/threads",
            json={
                "target_type": "plan",
                "initial_comment": "This should fail",
            },
        )
        assert response.status_code == 404


# ============================================================================
# Task Thread Endpoints
# ============================================================================


class TestListTaskThreads:
    def test_list_threads_empty(self, authed_client: TestClient, task: Task):
        response = authed_client.get(f"/api/v1/tasks/{task.id}/threads")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_threads_with_threads(
        self, authed_client: TestClient, task: Task, comment_thread_on_task: CommentThreadModel
    ):
        response = authed_client.get(f"/api/v1/tasks/{task.id}/threads")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(comment_thread_on_task.id)
        assert data[0]["target_type"] == "task"

    def test_list_threads_filter_by_type(
        self,
        authed_client: TestClient,
        task: Task,
        comment_thread_on_task: CommentThreadModel,
        comment_thread_on_code_line: CommentThreadModel,
    ):
        # Filter for task threads only
        response = authed_client.get(f"/api/v1/tasks/{task.id}/threads?target_type=task")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["target_type"] == "task"

        # Filter for code_line threads only
        response = authed_client.get(f"/api/v1/tasks/{task.id}/threads?target_type=code_line")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["target_type"] == "code_line"

    def test_list_threads_task_not_found(self, authed_client: TestClient):
        response = authed_client.get(f"/api/v1/tasks/{uuid4()}/threads")
        assert response.status_code == 404


class TestCreateTaskThread:
    def test_create_thread_on_task(self, authed_client: TestClient, task: Task):
        response = authed_client.post(
            f"/api/v1/tasks/{task.id}/threads",
            json={
                "target_type": "task",
                "initial_comment": "This is a comment on the task",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["target_type"] == "task"
        assert data["target_id"] == str(task.id)

    def test_create_thread_on_code_line(self, authed_client: TestClient, task: Task):
        response = authed_client.post(
            f"/api/v1/tasks/{task.id}/threads",
            json={
                "target_type": "code_line",
                "file_path": "src/app.py",
                "line_number": 10,
                "initial_comment": "This variable should be renamed",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["target_type"] == "code_line"
        assert data["file_path"] == "src/app.py"
        assert data["line_number"] == 10

    def test_create_code_line_thread_missing_file_path(self, authed_client: TestClient, task: Task):
        response = authed_client.post(
            f"/api/v1/tasks/{task.id}/threads",
            json={
                "target_type": "code_line",
                "line_number": 10,
                "initial_comment": "Missing file_path",
            },
        )
        assert response.status_code == 400
        assert "file_path is required" in response.json()["detail"]

    def test_create_code_line_thread_missing_line_number(
        self, authed_client: TestClient, task: Task
    ):
        response = authed_client.post(
            f"/api/v1/tasks/{task.id}/threads",
            json={
                "target_type": "code_line",
                "file_path": "src/app.py",
                "initial_comment": "Missing line_number",
            },
        )
        assert response.status_code == 400
        assert "line_number is required" in response.json()["detail"]

    def test_create_thread_wrong_target_type(self, authed_client: TestClient, task: Task):
        response = authed_client.post(
            f"/api/v1/tasks/{task.id}/threads",
            json={
                "target_type": "plan",
                "initial_comment": "This should fail",
            },
        )
        assert response.status_code == 400
        assert "target_type must be 'task' or 'code_line'" in response.json()["detail"]

    def test_create_thread_task_not_found(self, authed_client: TestClient):
        response = authed_client.post(
            f"/api/v1/tasks/{uuid4()}/threads",
            json={
                "target_type": "task",
                "initial_comment": "This should fail",
            },
        )
        assert response.status_code == 404


# ============================================================================
# Thread Endpoints
# ============================================================================


class TestGetThread:
    def test_get_thread(
        self, authed_client: TestClient, comment_thread_on_plan: CommentThreadModel
    ):
        response = authed_client.get(f"/api/v1/threads/{comment_thread_on_plan.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(comment_thread_on_plan.id)
        assert data["target_type"] == "plan"
        assert data["status"] == "open"
        assert len(data["comments"]) == 1
        assert data["comments"][0]["content"] == "Initial comment on plan"

    def test_get_thread_not_found(self, authed_client: TestClient):
        response = authed_client.get(f"/api/v1/threads/{uuid4()}")
        assert response.status_code == 404


class TestResolveThread:
    def test_resolve_thread(
        self, authed_client: TestClient, comment_thread_on_plan: CommentThreadModel
    ):
        response = authed_client.post(f"/api/v1/threads/{comment_thread_on_plan.id}/resolve")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"

    def test_resolve_already_resolved_thread(
        self,
        authed_client: TestClient,
        session: Session,
        comment_thread_on_plan: CommentThreadModel,
    ):
        # First, resolve the thread
        comment_thread_on_plan.status = CommentThreadStatus.RESOLVED
        session.flush()

        # Try to resolve again
        response = authed_client.post(f"/api/v1/threads/{comment_thread_on_plan.id}/resolve")
        assert response.status_code == 409
        assert "already resolved" in response.json()["detail"]

    def test_resolve_thread_not_found(self, authed_client: TestClient):
        response = authed_client.post(f"/api/v1/threads/{uuid4()}/resolve")
        assert response.status_code == 404


class TestListThreadComments:
    def test_list_comments(
        self, authed_client: TestClient, comment_thread_on_plan: CommentThreadModel
    ):
        response = authed_client.get(f"/api/v1/threads/{comment_thread_on_plan.id}/comments")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["content"] == "Initial comment on plan"

    def test_list_comments_thread_not_found(self, authed_client: TestClient):
        response = authed_client.get(f"/api/v1/threads/{uuid4()}/comments")
        assert response.status_code == 404


class TestCreateComment:
    def test_create_comment(
        self, authed_client: TestClient, comment_thread_on_plan: CommentThreadModel
    ):
        response = authed_client.post(
            f"/api/v1/threads/{comment_thread_on_plan.id}/comments",
            json={"content": "This is a reply"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "This is a reply"
        assert data["thread_id"] == str(comment_thread_on_plan.id)
        assert data["parent_comment_id"] is None

    def test_create_reply_comment(
        self,
        authed_client: TestClient,
        session: Session,
        comment_thread_on_plan: CommentThreadModel,
    ):
        # Get the initial comment ID
        initial_comment = comment_thread_on_plan.comments[0]

        response = authed_client.post(
            f"/api/v1/threads/{comment_thread_on_plan.id}/comments",
            json={
                "content": "This is a nested reply",
                "parent_comment_id": str(initial_comment.id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "This is a nested reply"
        assert data["parent_comment_id"] == str(initial_comment.id)

    def test_create_comment_invalid_parent(
        self, authed_client: TestClient, comment_thread_on_plan: CommentThreadModel
    ):
        response = authed_client.post(
            f"/api/v1/threads/{comment_thread_on_plan.id}/comments",
            json={
                "content": "Reply to non-existent comment",
                "parent_comment_id": str(uuid4()),
            },
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_create_comment_parent_from_different_thread(
        self,
        authed_client: TestClient,
        session: Session,
        comment_thread_on_plan: CommentThreadModel,
        comment_thread_on_task: CommentThreadModel,
    ):
        # Get comment from task thread
        task_comment = comment_thread_on_task.comments[0]

        # Try to reply using it as parent in plan thread
        response = authed_client.post(
            f"/api/v1/threads/{comment_thread_on_plan.id}/comments",
            json={
                "content": "Invalid cross-thread reply",
                "parent_comment_id": str(task_comment.id),
            },
        )
        assert response.status_code == 400
        assert "does not belong to the same thread" in response.json()["detail"]

    def test_create_comment_thread_not_found(self, authed_client: TestClient):
        response = authed_client.post(
            f"/api/v1/threads/{uuid4()}/comments",
            json={"content": "This should fail"},
        )
        assert response.status_code == 404
