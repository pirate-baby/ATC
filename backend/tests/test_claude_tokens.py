"""Tests for Claude subscription token pooling system."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.claude_token import ClaudeToken
from app.models.enums import ClaudeTokenStatus
from app.models.user import User
from app.services.encryption import decrypt_token, encrypt_token, mask_token


# ============================================================================
# Encryption Tests
# ============================================================================


def test_encrypt_decrypt_token():
    """Test that encryption and decryption work correctly."""
    original_token = "sk-ant-test123456789"
    encrypted = encrypt_token(original_token)

    # Encrypted token should be different from original
    assert encrypted != original_token

    # Decryption should return original token
    decrypted = decrypt_token(encrypted)
    assert decrypted == original_token


def test_mask_token():
    """Test token masking for display."""
    # Long token
    token = "sk-ant-api01-1234567890abcdef"
    masked = mask_token(token)
    assert "..." in masked
    assert masked.endswith("cdef")
    assert "1234567890" not in masked

    # Short token
    short_token = "short"
    masked_short = mask_token(short_token)
    assert masked_short == "****"


# ============================================================================
# API Endpoint Tests
# ============================================================================


def test_get_my_token_none(authed_client):
    """Test getting token when user has none."""
    response = authed_client.get("/api/v1/claude-tokens/me")
    assert response.status_code == 200
    assert response.json() is None


def test_create_token(authed_client, user: User, session: Session):
    """Test creating a new token."""
    response = authed_client.post(
        "/api/v1/claude-tokens",
        json={
            "name": "My Personal Token",
            "token": "sk-ant-test-token-12345678901234567890",
        },
    )
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "My Personal Token"
    assert data["status"] == "active"
    assert "..." in data["token_preview"]  # Masked token
    assert data["request_count"] == 0

    # Verify token was stored encrypted
    db_token = session.query(ClaudeToken).filter_by(user_id=user.id).first()
    assert db_token is not None
    assert db_token.encrypted_token != "sk-ant-test-token-12345678901234567890"

    # Verify we can decrypt it
    decrypted = decrypt_token(db_token.encrypted_token)
    assert decrypted == "sk-ant-test-token-12345678901234567890"


def test_create_token_duplicate(authed_client, user: User, session: Session):
    """Test that users can only have one token."""
    # Create first token
    token = ClaudeToken(
        user_id=user.id,
        name="Existing Token",
        encrypted_token=encrypt_token("sk-ant-existing"),
        status=ClaudeTokenStatus.ACTIVE,
    )
    session.add(token)
    session.flush()

    # Try to create another
    response = authed_client.post(
        "/api/v1/claude-tokens",
        json={
            "name": "New Token",
            "token": "sk-ant-new-token",
        },
    )
    assert response.status_code == 409
    assert "already have a token" in response.json()["detail"]


def test_update_token_name(authed_client, user: User, session: Session):
    """Test updating token name only."""
    token = ClaudeToken(
        user_id=user.id,
        name="Old Name",
        encrypted_token=encrypt_token("sk-ant-test"),
        status=ClaudeTokenStatus.ACTIVE,
    )
    session.add(token)
    session.flush()

    response = authed_client.patch(
        "/api/v1/claude-tokens/me",
        json={"name": "New Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_update_token_value(authed_client, user: User, session: Session):
    """Test updating token value resets status."""
    token = ClaudeToken(
        user_id=user.id,
        name="My Token",
        encrypted_token=encrypt_token("sk-ant-old"),
        status=ClaudeTokenStatus.INVALID,
        last_error="Old error",
    )
    session.add(token)
    session.flush()

    response = authed_client.patch(
        "/api/v1/claude-tokens/me",
        json={"token": "sk-ant-new-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["last_error"] is None


def test_delete_token(authed_client, user: User, session: Session):
    """Test removing a token."""
    token = ClaudeToken(
        user_id=user.id,
        name="To Delete",
        encrypted_token=encrypt_token("sk-ant-test"),
        status=ClaudeTokenStatus.ACTIVE,
    )
    session.add(token)
    session.flush()

    response = authed_client.delete("/api/v1/claude-tokens/me")
    assert response.status_code == 204

    # Verify it's gone
    db_token = session.query(ClaudeToken).filter_by(user_id=user.id).first()
    assert db_token is None


def test_delete_token_not_found(authed_client):
    """Test deleting when user has no token."""
    response = authed_client.delete("/api/v1/claude-tokens/me")
    assert response.status_code == 404


# ============================================================================
# Pool Status Tests
# ============================================================================


def test_pool_status_empty(authed_client):
    """Test pool status with no tokens."""
    response = authed_client.get("/api/v1/claude-tokens/pool/status")
    assert response.status_code == 200

    data = response.json()
    assert data["total_contributors"] == 0
    assert data["active_tokens"] == 0
    assert data["pool_health"] == "exhausted"


def test_pool_status_with_tokens(authed_client, session: Session):
    """Test pool status with various token states."""
    # Create users and tokens
    for i in range(5):
        user = User(
            git_handle=f"user{i}",
            email=f"user{i}@example.com",
        )
        session.add(user)
        session.flush()

        status = (
            ClaudeTokenStatus.ACTIVE if i < 3
            else ClaudeTokenStatus.RATE_LIMITED if i < 4
            else ClaudeTokenStatus.INVALID
        )
        token = ClaudeToken(
            user_id=user.id,
            name=f"Token {i}",
            encrypted_token=encrypt_token(f"sk-ant-test-{i}"),
            status=status,
            request_count=i * 10,
        )
        session.add(token)

    session.flush()

    response = authed_client.get("/api/v1/claude-tokens/pool/status")
    assert response.status_code == 200

    data = response.json()
    assert data["total_contributors"] == 5
    assert data["active_tokens"] == 3
    assert data["rate_limited_tokens"] == 1
    assert data["invalid_tokens"] == 1
    assert data["pool_health"] == "healthy"  # 3+ active = healthy


def test_pool_stats(authed_client, session: Session):
    """Test detailed pool statistics."""
    # Create users with varying request counts
    request_counts = [0, 5, 15, 50, 150, 600]
    for i, count in enumerate(request_counts):
        user = User(
            git_handle=f"statuser{i}",
            email=f"statuser{i}@example.com",
        )
        session.add(user)
        session.flush()

        token = ClaudeToken(
            user_id=user.id,
            name=f"Token {i}",
            encrypted_token=encrypt_token(f"sk-ant-stat-{i}"),
            status=ClaudeTokenStatus.ACTIVE,
            request_count=count,
        )
        session.add(token)

    session.flush()

    response = authed_client.get("/api/v1/claude-tokens/pool/stats")
    assert response.status_code == 200

    data = response.json()
    assert data["status"]["total_contributors"] == 6
    assert len(data["usage_distribution"]) > 0
    assert 0 <= data["fairness_score"] <= 1


# ============================================================================
# Token Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_token_success(authed_client, user: User, session: Session):
    """Test token validation with mocked API call."""
    token = ClaudeToken(
        user_id=user.id,
        name="To Validate",
        encrypted_token=encrypt_token("sk-ant-valid-token"),
        status=ClaudeTokenStatus.ACTIVE,
    )
    session.add(token)
    session.flush()

    # Mock the HTTP call
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        response = authed_client.post("/api/v1/claude-tokens/validate")
        assert response.status_code == 200

        data = response.json()
        assert data["valid"] is True


@pytest.mark.asyncio
async def test_validate_token_invalid(authed_client, user: User, session: Session):
    """Test token validation when API rejects token."""
    token = ClaudeToken(
        user_id=user.id,
        name="Invalid Token",
        encrypted_token=encrypt_token("sk-ant-invalid"),
        status=ClaudeTokenStatus.ACTIVE,
    )
    session.add(token)
    session.flush()

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        mock_response.content = b'{"error": {"message": "Invalid API key"}}'
        mock_post.return_value = mock_response

        response = authed_client.post("/api/v1/claude-tokens/validate")
        assert response.status_code == 200

        data = response.json()
        assert data["valid"] is False
        assert "Invalid API key" in data["error"]


# ============================================================================
# Token Pool Rotation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_available_token_returns_least_used(session: Session):
    """Test that pool rotation returns least-used token."""
    from app.routers.claude_tokens import get_available_token

    # Create users and tokens with different usage
    users_tokens = []
    for i, count in enumerate([100, 10, 50]):  # Middle one should be selected
        user = User(
            git_handle=f"pooluser{i}",
            email=f"pooluser{i}@example.com",
        )
        session.add(user)
        session.flush()

        token = ClaudeToken(
            user_id=user.id,
            name=f"Pool Token {i}",
            encrypted_token=encrypt_token(f"sk-ant-pool-{i}"),
            status=ClaudeTokenStatus.ACTIVE,
            request_count=count,
        )
        session.add(token)
        users_tokens.append((user, token))

    session.flush()

    # Get available token - should be the one with count=10
    result = await get_available_token(session)
    assert result is not None

    token_value, token_id = result
    assert token_value == "sk-ant-pool-1"  # The one with count=10


@pytest.mark.asyncio
async def test_record_token_usage_success(session: Session):
    """Test recording successful token usage."""
    from app.routers.claude_tokens import record_token_usage

    user = User(
        git_handle="usageuser",
        email="usageuser@example.com",
    )
    session.add(user)
    session.flush()

    token = ClaudeToken(
        user_id=user.id,
        name="Usage Token",
        encrypted_token=encrypt_token("sk-ant-usage"),
        status=ClaudeTokenStatus.ACTIVE,
        request_count=5,
    )
    session.add(token)
    session.flush()

    await record_token_usage(session, token.id, success=True)

    session.refresh(token)
    assert token.request_count == 6
    assert token.last_used_at is not None
    assert token.last_error is None


@pytest.mark.asyncio
async def test_record_token_usage_rate_limited(session: Session):
    """Test recording rate-limited token usage."""
    from app.routers.claude_tokens import record_token_usage

    user = User(
        git_handle="ratelimituser",
        email="ratelimituser@example.com",
    )
    session.add(user)
    session.flush()

    token = ClaudeToken(
        user_id=user.id,
        name="Rate Limited Token",
        encrypted_token=encrypt_token("sk-ant-ratelimit"),
        status=ClaudeTokenStatus.ACTIVE,
        request_count=0,
    )
    session.add(token)
    session.flush()

    await record_token_usage(session, token.id, success=False, rate_limited=True)

    session.refresh(token)
    assert token.status == ClaudeTokenStatus.RATE_LIMITED
    assert token.rate_limit_reset_at is not None
    assert token.request_count == 1


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_create_token_empty_name(authed_client):
    """Test that empty name is rejected."""
    response = authed_client.post(
        "/api/v1/claude-tokens",
        json={
            "name": "",
            "token": "sk-ant-test-token",
        },
    )
    assert response.status_code == 422  # Validation error


def test_create_token_short_token(authed_client):
    """Test that too-short token is rejected."""
    response = authed_client.post(
        "/api/v1/claude-tokens",
        json={
            "name": "Test Token",
            "token": "short",
        },
    )
    assert response.status_code == 422  # Validation error
