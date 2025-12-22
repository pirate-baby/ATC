"""Test fixtures for ATC Backend."""

import os
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("JWT_SECRET_KEY", "atc-dev-jwt-secret-do-not-use-in-production")

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import Base, Plan, PlanTaskStatus, Project, Task, User


# ============================================================================
# Auth Fixtures
# ============================================================================


def create_test_token(user_id: str | None = None) -> str:
    payload = {
        "sub": user_id or str(uuid4()),
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest.fixture
def auth_headers():
    token = create_test_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def authed_client(client, auth_headers):
    client.headers.update(auth_headers)
    return client


# ============================================================================
# Database Fixtures
# ============================================================================


def _create_tables_sqlite(engine):
    """Create tables for SQLite testing.

    NOTE: We cannot use Base.metadata.create_all() because the models use
    PostgreSQL-specific types (JSONB, ARRAY) that SQLite doesn't support.
    This manual schema definition is required for SQLite compatibility.

    IMPORTANT: When adding new columns to models, you MUST also add them here
    to keep the test schema in sync. This is a known trade-off for using
    SQLite in tests instead of PostgreSQL.
    """
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))

        # Users (no deps)
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                git_handle TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                display_name TEXT,
                avatar_url TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """
            )
        )

        # HATs (no deps)
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS hats (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME
            )
        """
            )
        )

        # Triage connections (no deps)
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS triage_connections (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                provider TEXT NOT NULL,
                config TEXT,
                last_sync_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """
            )
        )

        # Projects (deps: triage_connections)
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                git_url TEXT NOT NULL,
                main_branch TEXT DEFAULT 'main' NOT NULL,
                triage_connection_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME
            )
        """
            )
        )

        # Project settings (deps: projects) - TEXT instead of ARRAY for SQLite
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS project_settings (
                id TEXT PRIMARY KEY,
                project_id TEXT UNIQUE NOT NULL,
                required_approvals_plan INTEGER DEFAULT 1 NOT NULL,
                required_approvals_task INTEGER DEFAULT 1 NOT NULL,
                auto_approve_main_updates BOOLEAN DEFAULT 0 NOT NULL,
                assigned_hats TEXT DEFAULT '[]' NOT NULL
            )
        """
            )
        )

        # Plans (deps: projects, users, tasks)
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                parent_task_id TEXT,
                title TEXT NOT NULL,
                content TEXT,
                status TEXT DEFAULT 'backlog' NOT NULL,
                version INTEGER DEFAULT 1 NOT NULL,
                created_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME
            )
        """
            )
        )

        # Tasks (deps: projects, plans)
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                plan_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'backlog' NOT NULL,
                branch_name TEXT,
                worktree_path TEXT,
                version INTEGER DEFAULT 1 NOT NULL,
                session_started_at DATETIME,
                session_ended_at DATETIME,
                session_output_log TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME
            )
        """
            )
        )

        # Task blocking (deps: tasks)
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS task_blocking (
                task_id TEXT NOT NULL,
                blocked_by_id TEXT NOT NULL,
                PRIMARY KEY (task_id, blocked_by_id)
            )
        """
            )
        )

        # Triage items (deps: triage_connections, plans)
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS triage_items (
                id TEXT PRIMARY KEY,
                connection_id TEXT NOT NULL,
                plan_id TEXT,
                external_id TEXT NOT NULL,
                title TEXT NOT NULL,
                external_url TEXT,
                description TEXT,
                status TEXT DEFAULT 'pending' NOT NULL,
                imported_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """
            )
        )

        # Comment threads
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS comment_threads (
                id TEXT PRIMARY KEY,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                file_path TEXT,
                line_number INTEGER,
                status TEXT DEFAULT 'open' NOT NULL,
                summary TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """
            )
        )

        # Comments (deps: comment_threads, users)
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                author_id TEXT NOT NULL,
                content TEXT NOT NULL,
                parent_comment_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME
            )
        """
            )
        )

        # Reviews (deps: users)
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                reviewer_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                comment TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """
            )
        )

        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()


@pytest.fixture(scope="function")
def engine():
    """Create a SQLite in-memory engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key support for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    _create_tables_sqlite(engine)

    yield engine


@pytest.fixture(scope="function")
def session(engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with overridden session dependency."""

    def override_get_db():
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def user(session: Session) -> User:
    """Create a test user."""
    user = User(
        git_handle="testuser",
        email="test@example.com",
        display_name="Test User",
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def project(session: Session) -> Project:
    """Create a test project without settings (settings tested separately)."""
    project = Project(
        name="Test Project",
        git_url="https://github.com/test/test.git",
        main_branch="main",
    )
    session.add(project)
    session.flush()
    return project


@pytest.fixture
def project_with_settings(session: Session) -> Project:
    """Create a test project with settings using raw SQL for SQLite compatibility."""
    import uuid

    project = Project(
        name="Test Project",
        git_url="https://github.com/test/test.git",
        main_branch="main",
    )
    session.add(project)
    session.flush()

    # Insert settings using raw SQL to avoid ARRAY issue
    settings_id = str(uuid.uuid4())
    session.execute(
        text(
            """
            INSERT INTO project_settings
                (id, project_id, required_approvals_plan, required_approvals_task,
                 auto_approve_main_updates, assigned_hats)
            VALUES (:id, :project_id, 1, 1, 0, '[]')
        """
        ),
        {"id": settings_id, "project_id": str(project.id)},
    )
    session.flush()

    # Refresh the project to load the settings
    session.expire(project)
    return project


@pytest.fixture
def plan(session: Session, project: Project) -> Plan:
    """Create a test plan."""
    plan = Plan(
        project_id=project.id,
        title="Test Plan",
        content="Test plan content",
    )
    session.add(plan)
    session.flush()
    return plan


@pytest.fixture
def task(session: Session, project: Project) -> Task:
    """Create a test task."""
    task = Task(
        project_id=project.id,
        title="Test Task",
        description="Test task description",
    )
    session.add(task)
    session.flush()
    return task


@pytest.fixture
def task_in_review(session: Session, project: Project) -> Task:
    """Create a test task in review status."""
    task = Task(
        project_id=project.id,
        title="Task In Review",
        description="Task in review state",
        status=PlanTaskStatus.REVIEW,
    )
    session.add(task)
    session.flush()
    return task


@pytest.fixture
def task_in_review_with_settings(session: Session, project_with_settings: Project) -> Task:
    """Create a test task in review status with project settings."""
    task = Task(
        project_id=project_with_settings.id,
        title="Task In Review",
        description="Task in review state",
        status=PlanTaskStatus.REVIEW,
    )
    session.add(task)
    session.flush()
    return task
