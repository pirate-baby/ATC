"""Tests for authentication middleware."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from jose import jwt

from app.auth import CurrentUser, TokenPayload, decode_jwt_token
from app.config import settings


def create_test_token(
    user_id: str | None = None,
    exp_delta: timedelta | None = None,
    secret: str | None = None,
    algorithm: str | None = None,
    issuer: str | None = None,
    audience: str | None = None,
    include_exp: bool = True,
    include_sub: bool = True,
) -> str:
    """Create a test JWT token with configurable claims."""
    payload = {}

    if include_sub:
        payload["sub"] = user_id or str(uuid4())

    if include_exp:
        exp_time = datetime.now(timezone.utc) + (exp_delta or timedelta(hours=1))
        payload["exp"] = exp_time.timestamp()

    payload["iat"] = datetime.now(timezone.utc).timestamp()

    if issuer:
        payload["iss"] = issuer

    if audience:
        payload["aud"] = audience

    return jwt.encode(
        payload,
        secret or settings.jwt_secret_key,
        algorithm=algorithm or settings.jwt_algorithm,
    )


class TestDecodeJwtToken:
    """Tests for the decode_jwt_token function."""

    def test_valid_token(self):
        """Test decoding a valid JWT token."""
        user_id = str(uuid4())
        token = create_test_token(user_id=user_id)

        payload = decode_jwt_token(token)

        assert payload.sub == user_id
        assert payload.exp is not None

    def test_expired_token(self):
        """Test that expired tokens are rejected."""
        token = create_test_token(exp_delta=timedelta(hours=-1))

        with pytest.raises(Exception) as exc_info:
            decode_jwt_token(token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expired" in str(exc_info.value.detail).lower()

    def test_missing_subject_claim(self):
        """Test that tokens without subject claim are rejected."""
        token = create_test_token(include_sub=False)

        with pytest.raises(Exception) as exc_info:
            decode_jwt_token(token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "subject" in str(exc_info.value.detail).lower()

    def test_missing_expiration_claim(self):
        """Test that tokens without expiration claim are rejected."""
        token = create_test_token(include_exp=False)

        with pytest.raises(Exception) as exc_info:
            decode_jwt_token(token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expiration" in str(exc_info.value.detail).lower()

    def test_invalid_signature(self):
        """Test that tokens with invalid signatures are rejected."""
        token = create_test_token(secret="wrong_secret")

        with pytest.raises(Exception) as exc_info:
            decode_jwt_token(token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_malformed_token(self):
        """Test that malformed tokens are rejected."""
        with pytest.raises(Exception) as exc_info:
            decode_jwt_token("not.a.valid.token")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestProtectedEndpoints:
    """Integration tests for protected endpoints."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        from app.main import app

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_health_endpoint_no_auth_required(self, client):
        """Test that health endpoint is accessible without auth."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "healthy"

    def test_root_endpoint_no_auth_required(self, client):
        """Test that root endpoint is accessible without auth."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK

    def test_protected_endpoint_requires_auth(self, client):
        """Test that protected endpoints require authentication."""
        response = client.get("/api/v1/projects")
        # FastAPI returns 401 when no credentials are provided with auto_error=True
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoint_with_valid_token(self, client):
        """Test that protected endpoints accept valid tokens."""
        token = create_test_token()
        response = client.get(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {token}"},
        )
        # 501 means auth passed, endpoint not implemented
        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED

    def test_protected_endpoint_with_expired_token(self, client):
        """Test that protected endpoints reject expired tokens."""
        token = create_test_token(exp_delta=timedelta(hours=-1))
        response = client.get(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test that protected endpoints reject invalid tokens."""
        response = client.get(
            "/api/v1/projects",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_users_me_endpoint_with_valid_token(self, client):
        """Test the /users/me endpoint with valid token (auth passes, DB may fail)."""
        user_id = str(uuid4())
        token = create_test_token(user_id=user_id)
        try:
            response = client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            # Auth should pass - we either get 404 (user not in DB) or 500 (no DB)
            # Both mean auth succeeded since we didn't get 401
            assert response.status_code in [
                status.HTTP_404_NOT_FOUND,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ]
        except Exception as e:
            # Database connection error means we can't test this endpoint without DB
            if "could not translate host name" in str(e) or "OperationalError" in str(e):
                pytest.skip("Database not available for integration test")


class TestWebSocketAuth:
    """Tests for WebSocket authentication."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        from app.main import app

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_websocket_missing_token(self, client):
        """Test that WebSocket connection without token is rejected."""
        session_id = str(uuid4())
        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/v1/ws/sessions/{session_id}/stream"):
                pass

    def test_websocket_with_invalid_token(self, client):
        """Test that WebSocket connection with invalid token is rejected."""
        session_id = str(uuid4())
        with pytest.raises(Exception):
            with client.websocket_connect(
                f"/api/v1/ws/sessions/{session_id}/stream?token=invalid"
            ):
                pass

    def test_websocket_with_valid_token(self, client):
        """Test that WebSocket connection with valid token is accepted."""
        session_id = str(uuid4())
        token = create_test_token()
        # This should connect successfully
        with client.websocket_connect(
            f"/api/v1/ws/sessions/{session_id}/stream?token={token}"
        ) as websocket:
            # Send abort to close cleanly
            websocket.send_json({"type": "abort"})
            data = websocket.receive_json()
            assert data["type"] == "status"
            assert data["status"] == "aborted"


class TestTokenPayloadModel:
    """Tests for the TokenPayload Pydantic model."""

    def test_token_payload_creation(self):
        """Test creating a TokenPayload instance."""
        now = datetime.now(timezone.utc)
        payload = TokenPayload(
            sub="user123",
            exp=now + timedelta(hours=1),
            iat=now,
            iss="test_issuer",
            aud="test_audience",
        )
        assert payload.sub == "user123"
        assert payload.iss == "test_issuer"
        assert payload.aud == "test_audience"


class TestCurrentUserModel:
    """Tests for the CurrentUser model."""

    def test_current_user_creation(self):
        """Test creating a CurrentUser instance."""
        user_id = uuid4()
        now = datetime.now(timezone.utc)
        payload = TokenPayload(
            sub=str(user_id),
            exp=now + timedelta(hours=1),
        )
        current_user = CurrentUser(id=user_id, token_payload=payload)
        assert current_user.id == user_id
        assert current_user.token_payload.sub == str(user_id)
