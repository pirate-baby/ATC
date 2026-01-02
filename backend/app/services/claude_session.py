"""Claude Code session management.

This module provides a standalone session manager for Claude Code interactions
that decouples session state from WebSocket connections. Sessions can persist
across disconnections and be resumed when users return.

IMPORTANT: This module uses the Claude Agent SDK with the local Claude Code CLI only.
It does NOT make direct HTTP calls to the Anthropic API. All communication goes through
the Claude Code CLI which handles API interactions internally using subscription tokens.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator
from uuid import UUID

logger = logging.getLogger(__name__)


class ClaudeSessionError(Exception):
    """Base exception for Claude session errors."""

    pass


class ClaudeRateLimitError(ClaudeSessionError):
    """Raised when Claude API returns rate limit error."""

    pass


class ClaudeSessionNotFoundError(ClaudeSessionError):
    """Raised when a session ID is not found."""

    pass


@dataclass
class SessionMessage:
    """A message in a Claude session stream."""

    type: str  # thought, output, error, done, session_init, tool_use, user_question
    content: str | None = None
    timestamp: str | None = None
    session_id: str | None = None
    tool: str | None = None
    input: dict | None = None
    question: str | None = None


@dataclass
class SessionConfig:
    """Configuration for a Claude session."""

    subscription_token: str
    cwd: Path
    max_turns: int = 10
    max_thinking_tokens: int = 10000
    permission_mode: str = "bypassPermissions"


class ClaudeSession:
    """Manages a Claude Code session with persistence across connections.

    Sessions are identified by a unique session_id from the Claude SDK and can be
    resumed even after WebSocket disconnections. This allows users to:
    - Close their browser and return later to continue a conversation
    - View session history
    - Manage long-running sessions independently of the transport layer

    Example:
        # Create or resume a session
        session = ClaudeSession.create(
            session_key="plan-123",
            config=SessionConfig(
                subscription_token=token,
                cwd=Path("/workspace")
            )
        )

        # Stream messages
        async for message in session.send_message("Hello"):
            print(message.type, message.content)

        # Resume later
        session = ClaudeSession.resume(session_key="plan-123", config=config)
    """

    def __init__(
        self,
        session_key: str,
        config: SessionConfig,
        sdk_session_id: str | None = None,
    ):
        """Initialize a Claude session.

        Args:
            session_key: Unique identifier for this session (e.g., "plan-123", "task-456", "demo")
            config: Session configuration
            sdk_session_id: Claude SDK session ID for resuming (None for new sessions)
        """
        self.session_key = session_key
        self.config = config
        self._sdk_session_id = sdk_session_id
        self._initialized = False

        logger.info(
            f"Initialized ClaudeSession with key='{session_key}', "
            f"sdk_session_id={sdk_session_id or '<new>'}"
        )

    @classmethod
    def create(cls, session_key: str, config: SessionConfig) -> "ClaudeSession":
        """Create a new Claude session.

        Args:
            session_key: Unique identifier for this session
            config: Session configuration

        Returns:
            A new ClaudeSession instance
        """
        logger.info(f"Creating new session with key='{session_key}'")
        return cls(session_key=session_key, config=config, sdk_session_id=None)

    @classmethod
    def resume(cls, session_key: str, config: SessionConfig, sdk_session_id: str) -> "ClaudeSession":
        """Resume an existing Claude session.

        Args:
            session_key: Unique identifier for the session to resume
            config: Session configuration
            sdk_session_id: Claude SDK session ID to resume

        Returns:
            A ClaudeSession instance resuming the specified session
        """
        logger.info(f"Resuming session with key='{session_key}', sdk_session_id='{sdk_session_id}'")
        return cls(session_key=session_key, config=config, sdk_session_id=sdk_session_id)

    @property
    def sdk_session_id(self) -> str | None:
        """Get the Claude SDK session ID.

        Returns:
            The SDK session ID if available, None otherwise
        """
        return self._sdk_session_id

    async def send_message(
        self,
        user_message: str,
    ) -> AsyncIterator[SessionMessage]:
        """Send a message to Claude and stream responses.

        Args:
            user_message: The user's message to send

        Yields:
            SessionMessage objects containing the streamed response

        Raises:
            ClaudeRateLimitError: If rate limited by Claude API
            ClaudeSessionError: If an error occurs during streaming
        """
        logger.info(
            f"Sending message to session '{self.session_key}': {len(user_message)} chars, "
            f"resume={'yes' if self._sdk_session_id else 'no'}"
        )

        try:
            from claude_agent_sdk import (
                AssistantMessage,
                ClaudeAgentOptions,
                SystemMessage,
                TextBlock,
                ThinkingBlock,
                ToolUseBlock,
                query,
            )
        except ImportError as e:
            logger.error(f"Claude Agent SDK not installed: {e!r}", exc_info=True)
            raise ClaudeSessionError(
                "Claude Agent SDK not installed. Run: pip install claude-agent-sdk"
            ) from e

        # Configure options with subscription token (OAuth token)
        logger.debug(
            f"Configuring Claude SDK for session '{self.session_key}': "
            f"cwd={self.config.cwd}, max_turns={self.config.max_turns}"
        )

        options = ClaudeAgentOptions(
            max_turns=self.config.max_turns,
            cwd=str(self.config.cwd),
            env={"CLAUDE_CODE_OAUTH_TOKEN": self.config.subscription_token},
            permission_mode=self.config.permission_mode,
            max_thinking_tokens=self.config.max_thinking_tokens,
        )

        # If we have a session_id, resume the session to maintain conversation history
        if self._sdk_session_id:
            logger.info(f"Resuming SDK session: {self._sdk_session_id}")
            options.resume = self._sdk_session_id

        # Stream responses with delta tracking to avoid content duplication
        try:
            logger.debug(
                f"Starting Claude SDK query for session '{self.session_key}': "
                f"message_length={len(user_message)}"
            )

            message_count = 0
            # Track previous lengths for each block to send only deltas
            thinking_blocks_prev_len: dict[int, int] = {}
            text_blocks_prev_len: dict[int, int] = {}

            async for message in query(prompt=user_message, options=options):
                timestamp = datetime.now(timezone.utc).isoformat()

                # Capture session_id from system init message
                if isinstance(message, SystemMessage):
                    if hasattr(message, "subtype") and message.subtype == "init":
                        init_session_id = getattr(message, "session_id", None)
                        if not init_session_id and hasattr(message, "data"):
                            init_session_id = message.data.get("session_id")
                        if init_session_id:
                            self._sdk_session_id = init_session_id
                            self._initialized = True
                            logger.info(
                                f"Captured SDK session_id for session '{self.session_key}': "
                                f"{init_session_id}"
                            )
                            yield SessionMessage(
                                type="session_init",
                                session_id=init_session_id,
                                timestamp=timestamp,
                            )

                if isinstance(message, AssistantMessage):
                    for idx, block in enumerate(message.content):
                        if isinstance(block, ThinkingBlock):
                            # Get the full content and calculate delta
                            full_content = block.thinking
                            prev_len = thinking_blocks_prev_len.get(idx, 0)
                            delta = full_content[prev_len:]

                            if delta:  # Only send if there's new content
                                message_count += 1
                                logger.debug(
                                    f"Session '{self.session_key}' thought delta #{message_count}: "
                                    f"{len(delta)} new chars (total: {len(full_content)})"
                                )
                                yield SessionMessage(
                                    type="thought",
                                    content=delta,
                                    timestamp=timestamp,
                                )
                                thinking_blocks_prev_len[idx] = len(full_content)

                        elif isinstance(block, TextBlock):
                            # Get the full content and calculate delta
                            full_content = block.text
                            prev_len = text_blocks_prev_len.get(idx, 0)
                            delta = full_content[prev_len:]

                            if delta:  # Only send if there's new content
                                message_count += 1
                                logger.debug(
                                    f"Session '{self.session_key}' text delta #{message_count}: "
                                    f"{len(delta)} new chars (total: {len(full_content)})"
                                )
                                yield SessionMessage(
                                    type="output",
                                    content=delta,
                                    timestamp=timestamp,
                                )
                                text_blocks_prev_len[idx] = len(full_content)

                        elif isinstance(block, ToolUseBlock):
                            # Send tool use information
                            message_count += 1
                            logger.debug(
                                f"Session '{self.session_key}' tool_use #{message_count}: {block.name}"
                            )

                            # Special handling for AskUserQuestion tool
                            if block.name == "AskUserQuestion":
                                yield SessionMessage(
                                    type="user_question",
                                    question=block.input.get("question", ""),
                                    timestamp=timestamp,
                                )
                            else:
                                yield SessionMessage(
                                    type="tool_use",
                                    tool=block.name,
                                    input=block.input,
                                    timestamp=timestamp,
                                )

            logger.info(
                f"Session '{self.session_key}' stream completed successfully "
                f"with {message_count} message deltas"
            )

        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"Error in session '{self.session_key}' stream: {e!r}", exc_info=True)
            if "rate" in error_str and "limit" in error_str:
                raise ClaudeRateLimitError(str(e)) from e
            raise ClaudeSessionError(f"Session stream error: {e}") from e

    def reset(self) -> None:
        """Reset the session, clearing all conversation history."""
        logger.info(f"Resetting session '{self.session_key}'")
        self._sdk_session_id = None
        self._initialized = False

    def is_initialized(self) -> bool:
        """Check if the session has been initialized with a Claude SDK session ID.

        Returns:
            True if the session has a valid SDK session ID, False otherwise
        """
        return self._initialized and self._sdk_session_id is not None


class ClaudeSessionManager:
    """Manages multiple Claude sessions.

    This class provides session lifecycle management including creation, resumption,
    and cleanup. It maintains a registry of active sessions keyed by session_key.

    Example:
        manager = ClaudeSessionManager()

        # Create a new session
        session = manager.get_or_create_session(
            session_key="plan-123",
            config=SessionConfig(...)
        )

        # Clear a session
        manager.clear_session("plan-123")

        # Resume a session
        session = manager.get_or_create_session(
            session_key="plan-123",
            config=SessionConfig(...),
            sdk_session_id="previous-session-id"
        )
    """

    def __init__(self):
        """Initialize the session manager."""
        self._sessions: dict[str, ClaudeSession] = {}
        logger.info("ClaudeSessionManager initialized")

    def get_or_create_session(
        self,
        session_key: str,
        config: SessionConfig,
        sdk_session_id: str | None = None,
    ) -> ClaudeSession:
        """Get an existing session or create a new one.

        Args:
            session_key: Unique identifier for the session
            config: Session configuration
            sdk_session_id: Optional SDK session ID to resume

        Returns:
            A ClaudeSession instance
        """
        # If we have a session_id to resume, check if we already have this session
        if sdk_session_id and session_key in self._sessions:
            existing_session = self._sessions[session_key]
            if existing_session.sdk_session_id == sdk_session_id:
                logger.info(
                    f"Returning existing session for key='{session_key}', "
                    f"sdk_session_id='{sdk_session_id}'"
                )
                return existing_session

        # Create new or resume session
        if sdk_session_id:
            session = ClaudeSession.resume(
                session_key=session_key,
                config=config,
                sdk_session_id=sdk_session_id,
            )
        else:
            session = ClaudeSession.create(session_key=session_key, config=config)

        self._sessions[session_key] = session
        logger.info(f"Registered session with key='{session_key}'")
        return session

    def get_session(self, session_key: str) -> ClaudeSession | None:
        """Get an existing session by key.

        Args:
            session_key: Unique identifier for the session

        Returns:
            The ClaudeSession instance if found, None otherwise
        """
        return self._sessions.get(session_key)

    def clear_session(self, session_key: str) -> bool:
        """Clear a session completely, removing it from the registry.

        Args:
            session_key: Unique identifier for the session to clear

        Returns:
            True if the session was found and cleared, False otherwise
        """
        if session_key in self._sessions:
            session = self._sessions.pop(session_key)
            session.reset()
            logger.info(f"Cleared session with key='{session_key}'")
            return True
        logger.warning(f"Attempted to clear non-existent session with key='{session_key}'")
        return False

    def reset_session(self, session_key: str) -> bool:
        """Reset a session's conversation history but keep it in the registry.

        Args:
            session_key: Unique identifier for the session to reset

        Returns:
            True if the session was found and reset, False otherwise
        """
        if session_key in self._sessions:
            self._sessions[session_key].reset()
            logger.info(f"Reset session with key='{session_key}'")
            return True
        logger.warning(f"Attempted to reset non-existent session with key='{session_key}'")
        return False

    def list_sessions(self) -> list[str]:
        """List all active session keys.

        Returns:
            List of session keys
        """
        return list(self._sessions.keys())


# Global session manager instance
session_manager = ClaudeSessionManager()
