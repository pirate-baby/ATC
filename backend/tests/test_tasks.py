"""Tests for Task CRUD endpoints."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Plan,
    PlanTaskStatus,
    Project,
    Review,
    ReviewDecision,
    ReviewTargetType,
    Task,
    User,
)


class TestListProjectTasks:
    def test_list_tasks_empty(self, authed_client: TestClient, project: Project):
        response = authed_client.get(f"/api/v1/projects/{project.id}/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["pages"] == 0

    def test_list_tasks_with_tasks(self, authed_client: TestClient, project: Project, task: Task):
        response = authed_client.get(f"/api/v1/projects/{project.id}/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(task.id)
        assert data["items"][0]["title"] == task.title
        assert data["total"] == 1

    def test_list_tasks_status_filter(
        self, authed_client: TestClient, session: Session, project: Project
    ):
        task1 = Task(
            project_id=project.id,
            title="Backlog Task",
            status=PlanTaskStatus.BACKLOG,
        )
        task2 = Task(
            project_id=project.id,
            title="Review Task",
            status=PlanTaskStatus.REVIEW,
        )
        session.add_all([task1, task2])
        session.flush()

        response = authed_client.get(
            f"/api/v1/projects/{project.id}/tasks", params={"status": "review"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "review"

    def test_list_tasks_pagination(
        self, authed_client: TestClient, session: Session, project: Project
    ):
        for i in range(25):
            task = Task(project_id=project.id, title=f"Task {i}")
            session.add(task)
        session.flush()

        response = authed_client.get(
            f"/api/v1/projects/{project.id}/tasks", params={"page": 2, "limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 25
        assert data["page"] == 2
        assert data["pages"] == 3

    def test_list_tasks_project_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.get(f"/api/v1/projects/{fake_id}/tasks")
        assert response.status_code == 404


class TestCreateTask:
    def test_create_task_minimal(self, authed_client: TestClient, project: Project):
        response = authed_client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": "New Task"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Task"
        assert data["project_id"] == str(project.id)
        assert data["status"] == "backlog"
        assert data["blocked_by"] == []

    def test_create_task_with_description(self, authed_client: TestClient, project: Project):
        response = authed_client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": "New Task", "description": "Task description"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Task description"

    def test_create_task_with_plan(self, authed_client: TestClient, project: Project, plan: Plan):
        response = authed_client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": "New Task", "plan_id": str(plan.id)},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["plan_id"] == str(plan.id)

    def test_create_task_with_blockers(
        self, authed_client: TestClient, session: Session, project: Project
    ):
        blocker_task = Task(project_id=project.id, title="Blocker Task")
        session.add(blocker_task)
        session.flush()

        response = authed_client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": "Blocked Task", "blocked_by": [str(blocker_task.id)]},
        )
        assert response.status_code == 201
        data = response.json()
        assert str(blocker_task.id) in data["blocked_by"]
        assert data["status"] == "blocked"

    def test_create_task_blocker_from_different_project(
        self, authed_client: TestClient, session: Session, project: Project
    ):
        other_project = Project(name="Other Project", git_url="https://github.com/other/other.git")
        session.add(other_project)
        session.flush()

        other_task = Task(project_id=other_project.id, title="Other Task")
        session.add(other_task)
        session.flush()

        response = authed_client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": "New Task", "blocked_by": [str(other_task.id)]},
        )
        assert response.status_code == 400
        assert "different project" in response.json()["detail"]

    def test_create_task_project_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.post(
            f"/api/v1/projects/{fake_id}/tasks",
            json={"title": "New Task"},
        )
        assert response.status_code == 404

    def test_create_task_plan_not_found(self, authed_client: TestClient, project: Project):
        fake_plan_id = uuid.uuid4()
        response = authed_client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": "New Task", "plan_id": str(fake_plan_id)},
        )
        assert response.status_code == 404


class TestGetTask:
    def test_get_task(self, authed_client: TestClient, task: Task):
        response = authed_client.get(f"/api/v1/tasks/{task.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(task.id)
        assert data["title"] == task.title
        assert "plan" in data
        assert "blocking_tasks" in data
        assert "reviews" in data
        assert "threads" in data
        assert "active_session" in data

    def test_get_task_with_plan(
        self, authed_client: TestClient, session: Session, project: Project, plan: Plan
    ):
        task = Task(project_id=project.id, plan_id=plan.id, title="Task with Plan")
        session.add(task)
        session.flush()

        response = authed_client.get(f"/api/v1/tasks/{task.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["plan"]["id"] == str(plan.id)
        assert data["plan"]["title"] == plan.title

    def test_get_task_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.get(f"/api/v1/tasks/{fake_id}")
        assert response.status_code == 404


class TestUpdateTask:
    def test_update_task_title(self, authed_client: TestClient, task: Task):
        original_version = task.version
        response = authed_client.patch(
            f"/api/v1/tasks/{task.id}",
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["version"] == original_version + 1

    def test_update_task_description(self, authed_client: TestClient, task: Task):
        response = authed_client.patch(
            f"/api/v1/tasks/{task.id}",
            json={"description": "Updated description"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"

    def test_update_task_no_changes(self, authed_client: TestClient, task: Task):
        original_version = task.version
        response = authed_client.patch(f"/api/v1/tasks/{task.id}", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == original_version

    def test_update_task_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.patch(f"/api/v1/tasks/{fake_id}", json={"title": "Updated"})
        assert response.status_code == 404


class TestDeleteTask:
    def test_delete_task(self, authed_client: TestClient, session: Session, task: Task):
        task_id = task.id
        response = authed_client.delete(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 204

        deleted = session.get(Task, task_id)
        assert deleted is None

    def test_delete_task_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.delete(f"/api/v1/tasks/{fake_id}")
        assert response.status_code == 404


class TestGetBlockingTasks:
    def test_get_blocking_tasks_empty(self, authed_client: TestClient, task: Task):
        response = authed_client.get(f"/api/v1/tasks/{task.id}/blocking")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_blocking_tasks(
        self, authed_client: TestClient, session: Session, project: Project
    ):
        blocker = Task(project_id=project.id, title="Blocker")
        blocked = Task(project_id=project.id, title="Blocked")
        session.add_all([blocker, blocked])
        session.flush()

        blocked.blocked_by = [blocker]
        session.flush()

        response = authed_client.get(f"/api/v1/tasks/{blocked.id}/blocking")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(blocker.id)

    def test_get_blocking_tasks_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.get(f"/api/v1/tasks/{fake_id}/blocking")
        assert response.status_code == 404


class TestSetBlockingTasks:
    def test_set_blocking_tasks(
        self, authed_client: TestClient, session: Session, project: Project
    ):
        blocker = Task(project_id=project.id, title="Blocker")
        blocked = Task(project_id=project.id, title="Blocked")
        session.add_all([blocker, blocked])
        session.flush()

        response = authed_client.put(
            f"/api/v1/tasks/{blocked.id}/blocking",
            json={"blocked_by": [str(blocker.id)]},
        )
        assert response.status_code == 200
        data = response.json()
        assert str(blocker.id) in data["blocked_by"]
        assert data["status"] == "blocked"

    def test_set_blocking_tasks_clears_blockers(
        self, authed_client: TestClient, session: Session, project: Project
    ):
        blocker = Task(project_id=project.id, title="Blocker")
        blocked = Task(
            project_id=project.id,
            title="Blocked",
            status=PlanTaskStatus.BLOCKED,
        )
        session.add_all([blocker, blocked])
        session.flush()

        blocked.blocked_by = [blocker]
        session.flush()

        response = authed_client.put(
            f"/api/v1/tasks/{blocked.id}/blocking",
            json={"blocked_by": []},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["blocked_by"] == []
        assert data["status"] == "backlog"

    def test_set_blocking_tasks_circular_self(
        self, authed_client: TestClient, session: Session, project: Project
    ):
        task = Task(project_id=project.id, title="Task")
        session.add(task)
        session.flush()

        response = authed_client.put(
            f"/api/v1/tasks/{task.id}/blocking",
            json={"blocked_by": [str(task.id)]},
        )
        assert response.status_code == 409
        assert "circular" in response.json()["detail"].lower()

    def test_set_blocking_tasks_circular_chain(
        self, authed_client: TestClient, session: Session, project: Project
    ):
        # Create A -> B -> C chain, then try to make C -> A (cycle)
        task_a = Task(project_id=project.id, title="Task A")
        task_b = Task(project_id=project.id, title="Task B")
        task_c = Task(project_id=project.id, title="Task C")
        session.add_all([task_a, task_b, task_c])
        session.flush()

        # A is blocked by B
        task_a.blocked_by = [task_b]
        # B is blocked by C
        task_b.blocked_by = [task_c]
        session.flush()

        # Try to make C blocked by A - creates cycle
        response = authed_client.put(
            f"/api/v1/tasks/{task_c.id}/blocking",
            json={"blocked_by": [str(task_a.id)]},
        )
        assert response.status_code == 409
        assert "circular" in response.json()["detail"].lower()

    def test_set_blocking_tasks_different_project(
        self, authed_client: TestClient, session: Session, project: Project
    ):
        other_project = Project(name="Other Project", git_url="https://github.com/other/other.git")
        session.add(other_project)
        session.flush()

        task = Task(project_id=project.id, title="Task")
        other_task = Task(project_id=other_project.id, title="Other Task")
        session.add_all([task, other_task])
        session.flush()

        response = authed_client.put(
            f"/api/v1/tasks/{task.id}/blocking",
            json={"blocked_by": [str(other_task.id)]},
        )
        assert response.status_code == 400
        assert "different project" in response.json()["detail"]

    def test_set_blocking_tasks_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.put(
            f"/api/v1/tasks/{fake_id}/blocking",
            json={"blocked_by": []},
        )
        assert response.status_code == 404


class TestDAGValidation:
    def test_dag_no_cycle_multiple_blockers(
        self, authed_client: TestClient, session: Session, project: Project
    ):
        # A, B both block C - no cycle
        task_a = Task(project_id=project.id, title="Task A")
        task_b = Task(project_id=project.id, title="Task B")
        task_c = Task(project_id=project.id, title="Task C")
        session.add_all([task_a, task_b, task_c])
        session.flush()

        response = authed_client.put(
            f"/api/v1/tasks/{task_c.id}/blocking",
            json={"blocked_by": [str(task_a.id), str(task_b.id)]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["blocked_by"]) == 2

    def test_dag_diamond_pattern_no_cycle(
        self, authed_client: TestClient, session: Session, project: Project
    ):
        # Diamond: A blocks B and C, B and C both block D
        task_a = Task(project_id=project.id, title="Task A")
        task_b = Task(project_id=project.id, title="Task B")
        task_c = Task(project_id=project.id, title="Task C")
        task_d = Task(project_id=project.id, title="Task D")
        session.add_all([task_a, task_b, task_c, task_d])
        session.flush()

        # B blocked by A
        task_b.blocked_by = [task_a]
        # C blocked by A
        task_c.blocked_by = [task_a]
        session.flush()

        # D blocked by B and C - should work (diamond, no cycle)
        response = authed_client.put(
            f"/api/v1/tasks/{task_d.id}/blocking",
            json={"blocked_by": [str(task_b.id), str(task_c.id)]},
        )
        assert response.status_code == 200

    def test_dag_cycle_indirect(
        self, authed_client: TestClient, session: Session, project: Project
    ):
        # A -> B -> C -> D, then try D -> A
        tasks = [Task(project_id=project.id, title=f"Task {i}") for i in range(4)]
        session.add_all(tasks)
        session.flush()

        # Create chain: A blocked by B, B blocked by C, C blocked by D
        tasks[0].blocked_by = [tasks[1]]
        tasks[1].blocked_by = [tasks[2]]
        tasks[2].blocked_by = [tasks[3]]
        session.flush()

        # Try D blocked by A - should fail (cycle)
        response = authed_client.put(
            f"/api/v1/tasks/{tasks[3].id}/blocking",
            json={"blocked_by": [str(tasks[0].id)]},
        )
        assert response.status_code == 409


class TestListTaskReviews:
    def test_list_reviews_empty(self, authed_client: TestClient, task: Task):
        response = authed_client.get(f"/api/v1/tasks/{task.id}/reviews")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_reviews_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.get(f"/api/v1/tasks/{fake_id}/reviews")
        assert response.status_code == 404


class TestCreateTaskReview:
    def test_create_review(
        self, authed_client: TestClient, session: Session, task_in_review: Task, user: User
    ):
        response = authed_client.post(
            f"/api/v1/tasks/{task_in_review.id}/reviews",
            params={"reviewer_id": str(user.id)},
            json={"decision": "approved", "comment": "LGTM"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["decision"] == "approved"
        assert data["comment"] == "LGTM"
        assert data["reviewer_id"] == str(user.id)

    def test_create_review_not_in_review_status(
        self, authed_client: TestClient, task: Task, user: User
    ):
        response = authed_client.post(
            f"/api/v1/tasks/{task.id}/reviews",
            params={"reviewer_id": str(user.id)},
            json={"decision": "approved"},
        )
        assert response.status_code == 409
        assert "not in review state" in response.json()["detail"]

    def test_create_review_task_not_found(self, authed_client: TestClient, user: User):
        fake_id = uuid.uuid4()
        response = authed_client.post(
            f"/api/v1/tasks/{fake_id}/reviews",
            params={"reviewer_id": str(user.id)},
            json={"decision": "approved"},
        )
        assert response.status_code == 404


class TestApproveTask:
    def test_approve_task(
        self, authed_client: TestClient, session: Session, task_in_review: Task, user: User
    ):
        review = Review(
            target_type=ReviewTargetType.TASK,
            target_id=task_in_review.id,
            reviewer_id=user.id,
            decision=ReviewDecision.APPROVED,
        )
        session.add(review)
        session.flush()

        response = authed_client.post(f"/api/v1/tasks/{task_in_review.id}/approve")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cicd"

    def test_approve_task_insufficient_approvals(
        self, authed_client: TestClient, task_in_review: Task
    ):
        response = authed_client.post(f"/api/v1/tasks/{task_in_review.id}/approve")
        assert response.status_code == 409
        assert "Insufficient approvals" in response.json()["detail"]

    def test_approve_task_not_in_review(self, authed_client: TestClient, task: Task):
        response = authed_client.post(f"/api/v1/tasks/{task.id}/approve")
        assert response.status_code == 409
        assert "not in review state" in response.json()["detail"]

    def test_approve_task_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.post(f"/api/v1/tasks/{fake_id}/approve")
        assert response.status_code == 404


class TestSpawnPlan:
    def test_spawn_plan(self, authed_client: TestClient, task: Task):
        response = authed_client.post(f"/api/v1/tasks/{task.id}/spawn-plan")
        assert response.status_code == 201
        data = response.json()
        assert data["parent_task_id"] == str(task.id)
        assert data["project_id"] == str(task.project_id)
        assert task.title in data["title"]

    def test_spawn_plan_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.post(f"/api/v1/tasks/{fake_id}/spawn-plan")
        assert response.status_code == 404


class TestGetTaskDiff:
    def test_get_diff_no_worktree(self, authed_client: TestClient, task: Task):
        """Task without worktree returns 404."""
        response = authed_client.get(f"/api/v1/tasks/{task.id}/diff")
        assert response.status_code == 404
        assert "worktree" in response.json()["detail"].lower()

    def test_get_diff_task_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.get(f"/api/v1/tasks/{fake_id}/diff")
        assert response.status_code == 404
