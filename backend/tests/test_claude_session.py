"""Tests for Claude session management."""

from pathlib import Path

import pytest

from app.services.claude_session import (
    ClaudeSession,
    ClaudeSessionManager,
    SessionConfig,
)


def test_session_creation():
    """Test creating a new Claude session."""
    config = SessionConfig(
        subscription_token="test-token",
        cwd=Path("/tmp/test"),
    )

    session = ClaudeSession.create(session_key="test-session", config=config)

    assert session.session_key == "test-session"
    assert session.sdk_session_id is None
    assert not session.is_initialized()


def test_session_resume():
    """Test resuming a Claude session."""
    config = SessionConfig(
        subscription_token="test-token",
        cwd=Path("/tmp/test"),
    )

    session = ClaudeSession.resume(
        session_key="test-session",
        config=config,
        sdk_session_id="existing-session-id",
    )

    assert session.session_key == "test-session"
    assert session.sdk_session_id == "existing-session-id"


def test_session_reset():
    """Test resetting a Claude session."""
    config = SessionConfig(
        subscription_token="test-token",
        cwd=Path("/tmp/test"),
    )

    session = ClaudeSession.resume(
        session_key="test-session",
        config=config,
        sdk_session_id="existing-session-id",
    )

    assert session.sdk_session_id == "existing-session-id"

    session.reset()

    assert session.sdk_session_id is None
    assert not session.is_initialized()


def test_session_manager_create():
    """Test session manager creates new sessions."""
    manager = ClaudeSessionManager()
    config = SessionConfig(
        subscription_token="test-token",
        cwd=Path("/tmp/test"),
    )

    session = manager.get_or_create_session(
        session_key="test-1",
        config=config,
    )

    assert session.session_key == "test-1"
    assert "test-1" in manager.list_sessions()


def test_session_manager_resume():
    """Test session manager can resume existing sessions."""
    manager = ClaudeSessionManager()
    config = SessionConfig(
        subscription_token="test-token",
        cwd=Path("/tmp/test"),
    )

    # Create initial session
    session1 = manager.get_or_create_session(
        session_key="test-1",
        config=config,
        sdk_session_id="session-123",
    )

    # Get the same session again
    session2 = manager.get_or_create_session(
        session_key="test-1",
        config=config,
        sdk_session_id="session-123",
    )

    # Should be the same instance
    assert session1 is session2


def test_session_manager_clear():
    """Test session manager can clear sessions."""
    manager = ClaudeSessionManager()
    config = SessionConfig(
        subscription_token="test-token",
        cwd=Path("/tmp/test"),
    )

    # Create session
    session = manager.get_or_create_session(
        session_key="test-1",
        config=config,
    )

    assert "test-1" in manager.list_sessions()

    # Clear session
    result = manager.clear_session("test-1")

    assert result is True
    assert "test-1" not in manager.list_sessions()
    assert session.sdk_session_id is None


def test_session_manager_reset():
    """Test session manager can reset sessions."""
    manager = ClaudeSessionManager()
    config = SessionConfig(
        subscription_token="test-token",
        cwd=Path("/tmp/test"),
    )

    # Create session with SDK session ID
    session = manager.get_or_create_session(
        session_key="test-1",
        config=config,
        sdk_session_id="session-123",
    )

    assert session.sdk_session_id == "session-123"

    # Reset session
    result = manager.reset_session("test-1")

    assert result is True
    assert "test-1" in manager.list_sessions()  # Still in registry
    assert session.sdk_session_id is None  # But session is reset


def test_session_config():
    """Test session configuration."""
    config = SessionConfig(
        subscription_token="test-token",
        cwd=Path("/tmp/test"),
        max_turns=20,
        max_thinking_tokens=5000,
        permission_mode="ask",
    )

    assert config.subscription_token == "test-token"
    assert config.cwd == Path("/tmp/test")
    assert config.max_turns == 20
    assert config.max_thinking_tokens == 5000
    assert config.permission_mode == "ask"
