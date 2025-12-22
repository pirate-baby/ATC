import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jose import jwt

os.environ.setdefault("JWT_SECRET_KEY", "atc-dev-jwt-secret-do-not-use-in-production")

from app.config import settings
from app.main import app


def create_test_token(user_id: str | None = None) -> str:
    payload = {
        "sub": user_id or str(uuid4()),
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_test_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def authed_client(client, auth_headers):
    client.headers.update(auth_headers)
    return client
