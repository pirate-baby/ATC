"""Test fixtures for ATC Backend.

Uses PostgreSQL via docker-compose for testing to match production environment.
Run `docker compose up db` before running tests locally.
"""

import os
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Set test environment variables before importing app modules
os.environ.setdefault("JWT_SECRET_KEY", "atc-dev-jwt-secret-do-not-use-in-production")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://atc:atc_dev@localhost:5432/atc_test")

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import Base, Plan, PlanTaskStatus, Project, ProjectSettings, Task, User


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
def auth_headers(user: User) -> dict[str, str]:
    """Auth headers with a real user ID from the database.

    This fixture depends on 'user' to ensure the user exists in the database
    before creating the token, satisfying foreign key constraints.
    """
    token = create_test_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def authed_client(client, auth_headers):
    client.headers.update(auth_headers)
    return client


# ============================================================================
# Database Fixtures
# ============================================================================


def get_test_database_url() -> str:
    """Get the test database URL.

    Uses DATABASE_URL env var, defaulting to docker-compose db service.
    When running in docker (test service), db hostname is 'db'.
    When running locally, use 'localhost' with the exposed port.
    """
    # Check if we're in docker (db service available at 'db' hostname)
    default_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://atc:atc_dev@localhost:5432/atc_test",
    )
    # Replace the main database with test database
    if "/atc" in default_url and "/atc_test" not in default_url:
        default_url = default_url.replace("/atc", "/atc_test")
    return default_url


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Session-scoped test database URL."""
    return get_test_database_url()


@pytest.fixture(scope="session")
def engine(test_db_url: str):
    """Create a PostgreSQL engine for testing.

    Creates the test database if it doesn't exist, then creates all tables.
    """
    # First connect to default 'atc' database to create test database
    admin_url = test_db_url.replace("/atc_test", "/atc")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    with admin_engine.connect() as conn:
        # Check if test database exists
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'atc_test'")
        )
        if not result.fetchone():
            conn.execute(text("CREATE DATABASE atc_test"))

    admin_engine.dispose()

    # Now connect to test database and create tables
    test_engine = create_engine(test_db_url)
    Base.metadata.create_all(bind=test_engine)

    yield test_engine

    test_engine.dispose()


@pytest.fixture(scope="function")
def session(engine) -> Generator[Session, None, None]:
    """Create a database session for testing with transaction rollback.

    Each test runs in a transaction that is rolled back after the test,
    ensuring test isolation without needing to truncate tables.
    """
    connection = engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(bind=connection, expire_on_commit=False, autoflush=False)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with overridden session dependency."""

    def override_get_db():
        try:
            yield session
        except Exception:
            session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ============================================================================
# Entity Fixtures
# ============================================================================


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
    """Create a test project without settings."""
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
    """Create a test project with settings."""
    project = Project(
        name="Test Project",
        git_url="https://github.com/test/test.git",
        main_branch="main",
    )
    session.add(project)
    session.flush()

    project_settings = ProjectSettings(
        project_id=project.id,
        required_approvals_plan=1,
        required_approvals_task=1,
        auto_approve_main_updates=False,
        assigned_hats=[],
    )
    session.add(project_settings)
    session.flush()

    session.refresh(project)
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
