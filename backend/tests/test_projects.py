"""Tests for Project CRUD endpoints."""

import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Project, ProjectSettings


class TestListProjects:
    def test_list_projects_empty(self, authed_client: TestClient):
        response = authed_client.get("/api/v1/projects")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["pages"] == 0

    def test_list_projects_with_projects(
        self, authed_client: TestClient, project_with_settings: Project
    ):
        response = authed_client.get("/api/v1/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(project_with_settings.id)
        assert data["items"][0]["name"] == project_with_settings.name
        assert data["total"] == 1

    def test_list_projects_pagination(
        self, authed_client: TestClient, session: Session
    ):
        # Create 25 projects
        for i in range(25):
            project = Project(
                name=f"Project {i}",
                git_url=f"https://github.com/test/test{i}.git",
            )
            session.add(project)
            session.flush()
            settings = ProjectSettings(project_id=project.id)
            session.add(settings)
        session.flush()

        response = authed_client.get("/api/v1/projects", params={"page": 2, "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 25
        assert data["page"] == 2
        assert data["pages"] == 3


class TestCreateProject:
    def test_create_project_minimal(self, authed_client: TestClient):
        with patch("app.routers.projects._validate_git_url"):
            response = authed_client.post(
                "/api/v1/projects",
                json={
                    "name": "New Project",
                    "git_url": "https://github.com/test/test.git",
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Project"
        assert data["git_url"] == "https://github.com/test/test.git"
        assert data["main_branch"] == "main"
        assert "settings" in data
        assert data["settings"]["required_approvals_plan"] == 1
        assert data["settings"]["required_approvals_task"] == 1

    def test_create_project_with_custom_settings(self, authed_client: TestClient):
        with patch("app.routers.projects._validate_git_url"):
            response = authed_client.post(
                "/api/v1/projects",
                json={
                    "name": "New Project",
                    "git_url": "https://github.com/test/test.git",
                    "main_branch": "develop",
                    "settings": {
                        "required_approvals_plan": 2,
                        "required_approvals_task": 3,
                        "auto_approve_main_updates": True,
                    },
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["main_branch"] == "develop"
        assert data["settings"]["required_approvals_plan"] == 2
        assert data["settings"]["required_approvals_task"] == 3
        assert data["settings"]["auto_approve_main_updates"] is True

    def test_create_project_invalid_git_url(self, authed_client: TestClient):
        # Test with a path that doesn't exist
        response = authed_client.post(
            "/api/v1/projects",
            json={
                "name": "New Project",
                "git_url": "file:///nonexistent/path/repo.git",
            },
        )
        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]


class TestGetProject:
    def test_get_project(self, authed_client: TestClient, project_with_settings: Project):
        response = authed_client.get(f"/api/v1/projects/{project_with_settings.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(project_with_settings.id)
        assert data["name"] == project_with_settings.name
        assert "settings" in data

    def test_get_project_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.get(f"/api/v1/projects/{fake_id}")
        assert response.status_code == 404


class TestUpdateProject:
    def test_update_project_name(
        self, authed_client: TestClient, project_with_settings: Project
    ):
        response = authed_client.patch(
            f"/api/v1/projects/{project_with_settings.id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    def test_update_project_main_branch(
        self, authed_client: TestClient, project_with_settings: Project
    ):
        response = authed_client.patch(
            f"/api/v1/projects/{project_with_settings.id}",
            json={"main_branch": "develop"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["main_branch"] == "develop"

    def test_update_project_git_url(
        self, authed_client: TestClient, project_with_settings: Project
    ):
        with patch("app.routers.projects._validate_git_url"):
            response = authed_client.patch(
                f"/api/v1/projects/{project_with_settings.id}",
                json={"git_url": "https://github.com/new/repo.git"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["git_url"] == "https://github.com/new/repo.git"

    def test_update_project_no_changes(
        self, authed_client: TestClient, project_with_settings: Project
    ):
        response = authed_client.patch(
            f"/api/v1/projects/{project_with_settings.id}",
            json={},
        )
        assert response.status_code == 200

    def test_update_project_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.patch(
            f"/api/v1/projects/{fake_id}",
            json={"name": "Updated"},
        )
        assert response.status_code == 404


class TestDeleteProject:
    def test_delete_project(
        self, authed_client: TestClient, session: Session, project_with_settings: Project
    ):
        project_id = project_with_settings.id
        response = authed_client.delete(f"/api/v1/projects/{project_id}")
        assert response.status_code == 204

        deleted = session.get(Project, project_id)
        assert deleted is None

    def test_delete_project_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.delete(f"/api/v1/projects/{fake_id}")
        assert response.status_code == 404


class TestGetProjectSettings:
    def test_get_project_settings(
        self, authed_client: TestClient, project_with_settings: Project
    ):
        response = authed_client.get(
            f"/api/v1/projects/{project_with_settings.id}/settings"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["required_approvals_plan"] == 1
        assert data["required_approvals_task"] == 1
        assert data["auto_approve_main_updates"] is False
        assert data["assigned_hats"] == []

    def test_get_project_settings_project_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.get(f"/api/v1/projects/{fake_id}/settings")
        assert response.status_code == 404

    def test_get_project_settings_no_settings(
        self, authed_client: TestClient, project: Project
    ):
        # Project fixture creates project without settings
        response = authed_client.get(f"/api/v1/projects/{project.id}/settings")
        assert response.status_code == 404
        assert "settings not found" in response.json()["detail"]


class TestUpdateProjectSettings:
    def test_update_project_settings(
        self, authed_client: TestClient, project_with_settings: Project
    ):
        response = authed_client.patch(
            f"/api/v1/projects/{project_with_settings.id}/settings",
            json={
                "required_approvals_plan": 3,
                "auto_approve_main_updates": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["required_approvals_plan"] == 3
        assert data["auto_approve_main_updates"] is True
        # Unchanged field should remain the same
        assert data["required_approvals_task"] == 1

    def test_update_project_settings_no_changes(
        self, authed_client: TestClient, project_with_settings: Project
    ):
        response = authed_client.patch(
            f"/api/v1/projects/{project_with_settings.id}/settings",
            json={},
        )
        assert response.status_code == 200

    def test_update_project_settings_project_not_found(self, authed_client: TestClient):
        fake_id = uuid.uuid4()
        response = authed_client.patch(
            f"/api/v1/projects/{fake_id}/settings",
            json={"required_approvals_plan": 2},
        )
        assert response.status_code == 404

    def test_update_project_settings_no_settings(
        self, authed_client: TestClient, project: Project
    ):
        response = authed_client.patch(
            f"/api/v1/projects/{project.id}/settings",
            json={"required_approvals_plan": 2},
        )
        assert response.status_code == 404
        assert "settings not found" in response.json()["detail"]


class TestGitUrlValidation:
    def test_local_path_not_exists(self, authed_client: TestClient):
        response = authed_client.post(
            "/api/v1/projects",
            json={
                "name": "Test",
                "git_url": "file:///nonexistent/path",
            },
        )
        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]

    def test_local_path_not_git_repo(self, authed_client: TestClient, tmp_path):
        # Create a directory that is not a git repo
        non_git_dir = tmp_path / "not_a_repo"
        non_git_dir.mkdir()

        response = authed_client.post(
            "/api/v1/projects",
            json={
                "name": "Test",
                "git_url": f"file://{non_git_dir}",
            },
        )
        assert response.status_code == 400
        assert "not a git repository" in response.json()["detail"]

    def test_local_path_is_git_repo(self, authed_client: TestClient, tmp_path):
        # Create a directory with .git subdirectory
        git_dir = tmp_path / "my_repo"
        git_dir.mkdir()
        (git_dir / ".git").mkdir()

        response = authed_client.post(
            "/api/v1/projects",
            json={
                "name": "Test",
                "git_url": f"file://{git_dir}",
            },
        )
        assert response.status_code == 201
