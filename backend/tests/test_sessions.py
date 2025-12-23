"""Tests for CodingSession endpoints."""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CodingSession, Plan, PlanTaskStatus, Project, Task
from app.schemas.session import CodingSessionStatus, SessionTargetType

# WebSocket context manager requires the variable even though we don't use it
# ruff: noqa: F841


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def coding_session(session: Session, task: Task) -> CodingSession:
    """Create a running coding session for a task."""
    cs = CodingSession(
        target_type=SessionTargetType.TASK.value,
        target_id=task.id,
        status=CodingSessionStatus.RUNNING.value,
    )
    session.add(cs)
    session.flush()
    return cs


@pytest.fixture
def completed_session(session: Session, task: Task) -> CodingSession:
    """Create a completed coding session."""
    cs = CodingSession(
        target_type=SessionTargetType.TASK.value,
        target_id=task.id,
        status=CodingSessionStatus.COMPLETED.value,
        ended_at=datetime.now(timezone.utc),
    )
    session.add(cs)
    session.flush()
    return cs


@pytest.fixture
def aborted_session(session: Session, task: Task) -> CodingSession:
    """Create an aborted coding session."""
    cs = CodingSession(
        target_type=SessionTargetType.TASK.value,
        target_id=task.id,
        status=CodingSessionStatus.ABORTED.value,
        ended_at=datetime.now(timezone.utc),
    )
    session.add(cs)
    session.flush()
    return cs


@pytest.fixture
def plan_session(session: Session, plan: Plan) -> CodingSession:
    """Create a running coding session for a plan."""
    cs = CodingSession(
        target_type=SessionTargetType.PLAN.value,
        target_id=plan.id,
        status=CodingSessionStatus.RUNNING.value,
    )
    session.add(cs)
    session.flush()
    return cs


@pytest.fixture
def coding_task(session: Session, project: Project) -> Task:
    """Create a task in coding status."""
    task = Task(
        project_id=project.id,
        title="Coding Task",
        status=PlanTaskStatus.CODING,
    )
    session.add(task)
    session.flush()
    return task


@pytest.fixture
def coding_plan(session: Session, project: Project) -> Plan:
    """Create a plan in coding status."""
    plan = Plan(
        project_id=project.id,
        title="Coding Plan",
        status=PlanTaskStatus.CODING,
    )
    session.add(plan)
    session.flush()
    return plan


# ============================================================================
# List Sessions Tests
# ============================================================================


class TestListSessions:
    def test_list_sessions_empty(self, authed_client: TestClient):
        response = authed_client.get("/api/v1/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["pages"] == 0

    def test_list_sessions_with_sessions(
        self, authed_client: TestClient, coding_session: CodingSession
    ):
        response = authed_client.get("/api/v1/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(coding_session.id)
        assert data["items"][0]["status"] == "running"
        assert data["total"] == 1

    def test_list_sessions_status_filter_running(
        self,
        authed_client: TestClient,
        coding_session: CodingSession,
        completed_session: CodingSession,
    ):
        response = authed_client.get("/api/v1/sessions", params={"status": "running"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(coding_session.id)
        assert data["items"][0]["status"] == "running"

    def test_list_sessions_status_filter_completed(
        self,
        authed_client: TestClient,
        coding_session: CodingSession,
        completed_session: CodingSession,
    ):
        response = authed_client.get("/api/v1/sessions", params={"status": "completed"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(completed_session.id)
        assert data["items"][0]["status"] == "completed"

    def test_list_sessions_status_filter_aborted(
        self,
        authed_client: TestClient,
        coding_session: CodingSession,
        aborted_session: CodingSession,
    ):
        response = authed_client.get("/api/v1/sessions", params={"status": "aborted"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(aborted_session.id)
        assert data["items"][0]["status"] == "aborted"

    def test_list_sessions_pagination(
        self, authed_client: TestClient, session: Session, project: Project
    ):
        # Create multiple tasks with sessions
        for i in range(25):
            task = Task(project_id=project.id, title=f"Task {i}")
            session.add(task)
            session.flush()
            cs = CodingSession(
                target_type=SessionTargetType.TASK.value,
                target_id=task.id,
                status=CodingSessionStatus.RUNNING.value,
            )
            session.add(cs)
        session.flush()

        response = authed_client.get("/api/v1/sessions", params={"page": 2, "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 25
        assert data["page"] == 2
        assert data["pages"] == 3

    def test_list_sessions_unauthorized(self, client: TestClient):
        response = client.get("/api/v1/sessions")
        assert response.status_code == 401


# ============================================================================
# Get Session Tests
# ============================================================================


class TestGetSession:
    def test_get_session(self, authed_client: TestClient, coding_session: CodingSession):
        response = authed_client.get(f"/api/v1/sessions/{coding_session.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(coding_session.id)
        assert data["status"] == "running"
        assert data["target_type"] == "task"
        assert data["target_id"] == str(coding_session.target_id)
        assert data["started_at"] is not None
        assert data["ended_at"] is None

    def test_get_completed_session(
        self, authed_client: TestClient, completed_session: CodingSession
    ):
        response = authed_client.get(f"/api/v1/sessions/{completed_session.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["ended_at"] is not None

    def test_get_session_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.get(f"/api/v1/sessions/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_session_unauthorized(self, client: TestClient, coding_session: CodingSession):
        response = client.get(f"/api/v1/sessions/{coding_session.id}")
        assert response.status_code == 401


# ============================================================================
# Abort Session Tests
# ============================================================================


class TestAbortSession:
    def test_abort_running_task_session(
        self,
        authed_client: TestClient,
        session: Session,
        coding_task: Task,
    ):
        # Create a running session for the coding task
        cs = CodingSession(
            target_type=SessionTargetType.TASK.value,
            target_id=coding_task.id,
            status=CodingSessionStatus.RUNNING.value,
        )
        session.add(cs)
        session.flush()

        response = authed_client.post(f"/api/v1/sessions/{cs.id}/abort")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "aborted"
        assert data["ended_at"] is not None

        # Check task status changed to review
        session.refresh(coding_task)
        assert coding_task.status == PlanTaskStatus.REVIEW

    def test_abort_running_plan_session(
        self,
        authed_client: TestClient,
        session: Session,
        coding_plan: Plan,
    ):
        # Create a running session for the coding plan
        cs = CodingSession(
            target_type=SessionTargetType.PLAN.value,
            target_id=coding_plan.id,
            status=CodingSessionStatus.RUNNING.value,
        )
        session.add(cs)
        session.flush()

        response = authed_client.post(f"/api/v1/sessions/{cs.id}/abort")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "aborted"

        # Check plan status changed to review
        session.refresh(coding_plan)
        assert coding_plan.status == PlanTaskStatus.REVIEW

    def test_abort_completed_session_fails(
        self, authed_client: TestClient, completed_session: CodingSession
    ):
        response = authed_client.post(f"/api/v1/sessions/{completed_session.id}/abort")
        assert response.status_code == 409
        assert "not running" in response.json()["detail"].lower()

    def test_abort_already_aborted_session_fails(
        self, authed_client: TestClient, aborted_session: CodingSession
    ):
        response = authed_client.post(f"/api/v1/sessions/{aborted_session.id}/abort")
        assert response.status_code == 409
        assert "not running" in response.json()["detail"].lower()

    def test_abort_session_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.post(f"/api/v1/sessions/{fake_id}/abort")
        assert response.status_code == 404

    def test_abort_session_unauthorized(self, client: TestClient, coding_session: CodingSession):
        response = client.post(f"/api/v1/sessions/{coding_session.id}/abort")
        assert response.status_code == 401


# ============================================================================
# WebSocket Tests
# ============================================================================


class TestSessionStreamWebSocket:
    def test_websocket_missing_token(self, client: TestClient, coding_session: CodingSession):
        with pytest.raises(Exception):
            with client.websocket_connect(
                f"/api/v1/ws/sessions/{coding_session.id}/stream"
            ) as websocket:
                pass

    def test_websocket_session_not_found(self, client: TestClient, auth_headers):
        fake_id = uuid.uuid4()
        token = auth_headers["Authorization"].split(" ")[1]
        with pytest.raises(Exception):
            with client.websocket_connect(
                f"/api/v1/ws/sessions/{fake_id}/stream?token={token}"
            ) as websocket:
                pass

    def test_websocket_session_not_running(
        self, client: TestClient, completed_session: CodingSession, auth_headers
    ):
        token = auth_headers["Authorization"].split(" ")[1]
        with pytest.raises(Exception):
            with client.websocket_connect(
                f"/api/v1/ws/sessions/{completed_session.id}/stream?token={token}"
            ) as websocket:
                pass
