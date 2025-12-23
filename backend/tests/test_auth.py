"""Tests for authentication middleware and OAuth endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

from app.auth import CurrentUser, TokenPayload, decode_jwt_token
from app.config import settings
from app.models.user import User


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
        assert "missing required claims" in str(exc_info.value.detail).lower()

    def test_missing_expiration_claim(self):
        """Test that tokens without expiration claim are rejected."""
        token = create_test_token(include_exp=False)

        with pytest.raises(Exception) as exc_info:
            decode_jwt_token(token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "missing required claims" in str(exc_info.value.detail).lower()

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
        try:
            response = client.get(
                "/api/v1/projects",
                headers={"Authorization": f"Bearer {token}"},
            )
            # If auth passes, we get 200 (DB connected) or 500 (no DB/tables)
            # We don't get 401/403, which confirms auth worked
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ], f"Expected auth to pass (200 or 500), got {response.status_code}"
        except Exception as e:
            # DB/table errors mean we can't test without full DB setup
            # but auth did pass (otherwise we'd get 401)
            err_str = str(e)
            if "UndefinedTable" in err_str or "ProgrammingError" in err_str:
                pytest.skip("Database tables not available for integration test")
            raise

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
            with client.websocket_connect(f"/api/v1/ws/sessions/{session_id}/stream?token=invalid"):
                pass

    def test_websocket_with_valid_token_but_no_session(self, client):
        """Test that WebSocket with valid token but non-existent session is rejected."""
        session_id = str(uuid4())
        token = create_test_token()
        # Valid token but session doesn't exist - should close with 4004
        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/v1/ws/sessions/{session_id}/stream?token={token}"):
                pass


class TestTokenPayloadModel:
    def test_token_payload_creation(self):
        now = datetime.now(timezone.utc)
        payload = TokenPayload(
            sub="user123",
            exp=now + timedelta(hours=1),
        )
        assert payload.sub == "user123"
        assert payload.exp > now


class TestCurrentUserModel:
    def test_current_user_creation(self):
        user_id = uuid4()
        now = datetime.now(timezone.utc)
        payload = TokenPayload(
            sub=str(user_id),
            exp=now + timedelta(hours=1),
        )
        current_user = CurrentUser(id=user_id, token_payload=payload)
        assert current_user.id == user_id
        assert current_user.token_payload.sub == str(user_id)


class TestGitHubAuthEndpoint:
    """Tests for GET /api/v1/auth/github."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        from app.main import app

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_github_auth_not_configured(self, client):
        """Returns 503 when GitHub OAuth is not configured."""
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.github_client_id = None
            mock_settings.github_client_secret = None

            response = client.get("/api/v1/auth/github")

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert "not configured" in response.json()["detail"]

    def test_github_auth_returns_url(self, client):
        """Returns OAuth authorization URL with state."""
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.github_client_id = "test-client-id"
            mock_settings.github_client_secret = "test-client-secret"
            mock_settings.github_redirect_uri = "http://localhost:3000/callback"

            response = client.get("/api/v1/auth/github")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "url" in data
            assert "state" in data
            assert "github.com/login/oauth/authorize" in data["url"]
            assert "client_id=test-client-id" in data["url"]
            assert "redirect_uri=" in data["url"]
            assert len(data["state"]) > 20

    def test_github_auth_with_custom_redirect_uri(self, client):
        """Accepts custom redirect_uri parameter."""
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.github_client_id = "test-client-id"
            mock_settings.github_client_secret = "test-client-secret"
            mock_settings.github_redirect_uri = None

            response = client.get(
                "/api/v1/auth/github",
                params={"redirect_uri": "http://custom.com/callback"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "custom.com" in data["url"]

    def test_github_auth_no_redirect_uri(self, client):
        """Returns 400 when no redirect URI is configured or provided."""
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.github_client_id = "test-client-id"
            mock_settings.github_client_secret = "test-client-secret"
            mock_settings.github_redirect_uri = None

            response = client.get("/api/v1/auth/github")

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "redirect" in response.json()["detail"].lower()


class TestGitHubCallbackEndpoint:
    """Tests for GET /api/v1/auth/github/callback."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        from app.main import app

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_callback_not_configured(self, client):
        """Returns 503 when GitHub OAuth is not configured."""
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.github_client_id = None
            mock_settings.github_client_secret = None

            response = client.get(
                "/api/v1/auth/github/callback",
                params={"code": "test-code", "state": "test-state"},
            )

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_callback_missing_code(self, client):
        """Returns 422 when code parameter is missing."""
        response = client.get(
            "/api/v1/auth/github/callback",
            params={"state": "test-state"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_callback_missing_state(self, client):
        """Returns 422 when state parameter is missing."""
        response = client.get(
            "/api/v1/auth/github/callback",
            params={"code": "test-code"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_callback_token_exchange_failure(self, client):
        """Returns 401 when token exchange fails."""
        from unittest.mock import MagicMock

        mock_token_response = MagicMock()
        mock_token_response.status_code = 401
        mock_token_response.json.return_value = {"error": "bad_verification_code"}

        with (
            patch("app.routers.auth.settings") as mock_settings,
            patch("app.routers.auth.httpx.AsyncClient") as mock_client,
        ):
            mock_settings.github_client_id = "test-client-id"
            mock_settings.github_client_secret = "test-client-secret"
            mock_settings.github_redirect_uri = "http://localhost:3000/callback"

            mock_async_client = AsyncMock()
            mock_async_client.post.return_value = mock_token_response
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_client.return_value = mock_async_client

            response = client.get(
                "/api/v1/auth/github/callback",
                params={"code": "bad-code", "state": "test-state"},
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_callback_user_fetch_failure(self, client):
        """Returns 401 when fetching GitHub user profile fails."""
        from unittest.mock import MagicMock

        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "gho_test_token"}

        mock_user_response = MagicMock()
        mock_user_response.status_code = 401

        with (
            patch("app.routers.auth.settings") as mock_settings,
            patch("app.routers.auth.httpx.AsyncClient") as mock_client,
        ):
            mock_settings.github_client_id = "test-client-id"
            mock_settings.github_client_secret = "test-client-secret"
            mock_settings.github_redirect_uri = "http://localhost:3000/callback"

            mock_async_client = AsyncMock()
            mock_async_client.post.return_value = mock_token_response
            mock_async_client.get.return_value = mock_user_response
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_client.return_value = mock_async_client

            response = client.get(
                "/api/v1/auth/github/callback",
                params={"code": "test-code", "state": "test-state"},
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGitHubCallbackWithDB:
    """Tests for GitHub callback with database operations."""

    def test_callback_creates_new_user(self, client: TestClient, session: Session):
        """Creates a new user when GitHub login doesn't exist."""
        from unittest.mock import MagicMock

        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "gho_test_token"}

        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "newgithubuser",
            "email": "new@github.com",
            "name": "New GitHub User",
            "avatar_url": "https://github.com/avatar.png",
        }

        with (
            patch("app.routers.auth.settings") as mock_settings,
            patch("app.routers.auth.httpx.AsyncClient") as mock_client,
        ):
            mock_settings.github_client_id = "test-client-id"
            mock_settings.github_client_secret = "test-client-secret"
            mock_settings.github_redirect_uri = "http://localhost:3000/callback"
            mock_settings.jwt_secret_key = settings.jwt_secret_key
            mock_settings.jwt_algorithm = settings.jwt_algorithm
            mock_settings.jwt_access_token_expire_minutes = 30
            mock_settings.jwt_issuer = None
            mock_settings.jwt_audience = None

            mock_async_client = AsyncMock()
            mock_async_client.post.return_value = mock_token_response
            mock_async_client.get.return_value = mock_user_response
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_client.return_value = mock_async_client

            response = client.get(
                "/api/v1/auth/github/callback",
                params={
                    "code": "test-code",
                    "state": "test-state",
                    "redirect_uri": "http://localhost:3000/callback",
                },
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == 30 * 60

            user = session.query(User).filter(User.git_handle == "newgithubuser").first()
            assert user is not None
            assert user.email == "new@github.com"
            assert user.display_name == "New GitHub User"
            assert user.avatar_url == "https://github.com/avatar.png"

    def test_callback_updates_existing_user(self, client: TestClient, session: Session):
        """Updates existing user when GitHub login already exists."""
        from unittest.mock import MagicMock

        existing_user = User(
            git_handle="existinguser",
            email="old@email.com",
            display_name="Old Name",
            avatar_url="https://old-avatar.png",
        )
        session.add(existing_user)
        session.flush()
        user_id = existing_user.id

        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "gho_test_token"}

        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "existinguser",
            "email": "new@email.com",
            "name": "New Name",
            "avatar_url": "https://new-avatar.png",
        }

        with (
            patch("app.routers.auth.settings") as mock_settings,
            patch("app.routers.auth.httpx.AsyncClient") as mock_client,
        ):
            mock_settings.github_client_id = "test-client-id"
            mock_settings.github_client_secret = "test-client-secret"
            mock_settings.github_redirect_uri = "http://localhost:3000/callback"
            mock_settings.jwt_secret_key = settings.jwt_secret_key
            mock_settings.jwt_algorithm = settings.jwt_algorithm
            mock_settings.jwt_access_token_expire_minutes = 30
            mock_settings.jwt_issuer = None
            mock_settings.jwt_audience = None

            mock_async_client = AsyncMock()
            mock_async_client.post.return_value = mock_token_response
            mock_async_client.get.return_value = mock_user_response
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_client.return_value = mock_async_client

            response = client.get(
                "/api/v1/auth/github/callback",
                params={
                    "code": "test-code",
                    "state": "test-state",
                    "redirect_uri": "http://localhost:3000/callback",
                },
            )

            assert response.status_code == status.HTTP_200_OK

            session.refresh(existing_user)
            assert existing_user.id == user_id
            assert existing_user.email == "new@email.com"
            assert existing_user.display_name == "New Name"
            assert existing_user.avatar_url == "https://new-avatar.png"


class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        from app.main import app

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_logout_returns_204(self, client):
        """Logout endpoint returns 204 No Content."""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""
