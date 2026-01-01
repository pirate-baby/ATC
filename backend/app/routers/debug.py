"""Debug tools for Claude Code integration."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, RequireAuth
from app.database import get_db
from app.models.claude_token import ClaudeToken as ClaudeTokenModel
from app.models.user import User as UserModel
from app.routers.claude_tokens import get_available_token, record_token_usage
from app.schemas.base import StandardError
from app.services.encryption import decrypt_token

router = APIRouter()

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


from pydantic import BaseModel, Field


class UserWithToken(BaseModel):
    """User with their Claude token info."""

    user_id: UUID
    username: str  # Using git_handle as username
    email: str | None = None
    has_token: bool
    token_id: UUID | None = None
    token_name: str | None = None


class DebugChatMessage(BaseModel):
    """A chat message in the debug console."""

    role: str = Field(..., description="'user' or 'assistant'")
    content: str | list[dict] = Field(..., description="Text content or array of content blocks")


class DebugChatRequest(BaseModel):
    """Request to send a debug chat message."""

    messages: list[DebugChatMessage]
    use_token_id: UUID | None = Field(
        None, description="Optional token ID to use (admin only, defaults to pool rotation)"
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/debug/users-with-tokens",
    response_model=list[UserWithToken],
    summary="List users with tokens",
    description="Get all users and their Claude token status for token selection in debug console.",
    responses={401: {"model": StandardError, "description": "Unauthorized"}},
)
async def list_users_with_tokens(
    current_user: RequireAuth,
    db: Session = Depends(get_db),
) -> list[UserWithToken]:
    """Get all users with their token status."""
    users = db.scalars(select(UserModel)).all()

    result = []
    for user in users:
        token = db.scalar(select(ClaudeTokenModel).where(ClaudeTokenModel.user_id == user.id))

        result.append(
            UserWithToken(
                user_id=user.id,
                username=user.git_handle,  # Use git_handle as username
                email=user.email,
                has_token=token is not None,
                token_id=token.id if token is not None else None,
                token_name=token.name if token is not None else None,
            )
        )

    return result


@router.websocket("/ws/debug/claude-console")
async def debug_claude_console(websocket: WebSocket):
    """
    WebSocket endpoint for debug Claude Code console.

    Authentication: Pass JWT token as query parameter ?token={jwt}

    Client-to-Server messages:
    {
        "type": "chat",
        "messages": [{"role": "user", "content": "..."}],
        "use_token_id": "uuid-optional"
    }

    Server-to-Client messages:
    {
        "type": "thought",
        "content": "...",
        "timestamp": "..."
    }
    {
        "type": "output",
        "content": "...",
        "timestamp": "..."
    }
    {
        "type": "error",
        "error": "...",
        "timestamp": "..."
    }
    {
        "type": "done",
        "timestamp": "..."
    }
    """
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info(f"WebSocket connection attempt from {client_host}")

    # Accept connection first
    await websocket.accept()
    logger.info(f"WebSocket connection accepted from {client_host}")

    # Then validate the token
    token = websocket.query_params.get("token")
    if not token:
        logger.warning(f"WebSocket missing token from {client_host}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return

    try:
        from app.auth import decode_jwt_token
        from uuid import UUID
        token_payload = decode_jwt_token(token)
        user_id = UUID(token_payload.sub)
        current_user = CurrentUser(id=user_id, token_payload=token_payload)
        logger.info(f"WebSocket authenticated for user {current_user.id}")
    except Exception as e:
        logger.warning(f"WebSocket authentication failed for {client_host}: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        return

    db = next(iter(get_db()))
    try:
        await websocket.send_json(
            {"type": "status", "status": "connected", "timestamp": datetime.now(timezone.utc).isoformat()}
        )

        while True:
            try:
                data = await websocket.receive_json()
                logger.debug(f"Received WebSocket message from user {current_user.id}: type={data.get('type')}")

                if data.get("type") == "chat":
                    # Extract messages and optional token selection
                    messages = data.get("messages", [])
                    use_token_id = data.get("use_token_id")

                    logger.info(
                        f"Processing chat request from user {current_user.id}: "
                        f"{len(messages)} messages, token_id={use_token_id}"
                    )

                    if not messages:
                        logger.warning(f"Empty messages received from user {current_user.id}")
                        await websocket.send_json(
                            {
                                "type": "error",
                                "error": "No messages provided",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                        continue

                    # Get token to use
                    token_str = None
                    token_id = None

                    if use_token_id:
                        # Use specific token (verify it exists and belongs to a user)
                        logger.debug(f"Looking up specific token: {use_token_id}")
                        token = db.scalar(
                            select(ClaudeTokenModel).where(ClaudeTokenModel.id == UUID(use_token_id))
                        )
                        if not token:
                            logger.error(f"Token {use_token_id} not found for user {current_user.id}")
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "error": f"Token {use_token_id} not found",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                            )
                            continue

                        try:
                            token_str = decrypt_token(token.encrypted_token)
                            token_id = token.id
                            logger.info(f"Using specific token {token.name} (id: {token_id}) for user {current_user.id}")
                        except ValueError as e:
                            logger.error(
                                f"Failed to decrypt token {use_token_id} for user {current_user.id}: {e!r}",
                                exc_info=True,
                            )
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "error": f"Failed to decrypt token: {str(e)}",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                            )
                            continue
                    else:
                        # Use pool rotation
                        logger.debug(f"Getting token from pool for user {current_user.id}")
                        token_result = await get_available_token(db)
                        if not token_result:
                            logger.error(f"No available tokens in pool for user {current_user.id}")
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "error": "No available tokens in pool",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                            )
                            continue

                        token_str, token_id = token_result
                        logger.info(f"Using token from pool (id: {token_id}) for user {current_user.id}")

                    # Stream Claude response
                    success = False
                    rate_limited = False
                    error_message = None

                    logger.info(f"Starting Claude stream for user {current_user.id} with token {token_id}")

                    try:
                        async for message in _stream_claude_response(token_str, messages):
                            await websocket.send_json(message)

                        success = True
                        logger.info(f"Claude stream completed successfully for user {current_user.id}")
                        await websocket.send_json(
                            {"type": "done", "timestamp": datetime.now(timezone.utc).isoformat()}
                        )

                    except ClaudeRateLimitError as e:
                        rate_limited = True
                        error_message = str(e)
                        logger.warning(
                            f"Rate limited during Claude stream for user {current_user.id} with token {token_id}: {e}"
                        )
                        await websocket.send_json(
                            {
                                "type": "error",
                                "error": f"Rate limited: {str(e)}",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                    except Exception as e:
                        logger.error(
                            f"Error streaming Claude response for user {current_user.id}: {e!r}",
                            exc_info=True,
                        )
                        error_message = str(e)
                        await websocket.send_json(
                            {
                                "type": "error",
                                "error": str(e),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                    finally:
                        # Record token usage
                        if token_id:
                            logger.debug(
                                f"Recording token usage for token {token_id}: "
                                f"success={success}, rate_limited={rate_limited}"
                            )
                            await record_token_usage(
                                db=db,
                                token_id=token_id,
                                success=success,
                                rate_limited=rate_limited,
                                error_message=error_message,
                            )
                            db.commit()

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {current_user.id}")
                break
            except Exception as e:
                logger.error(
                    f"Unhandled error in debug console websocket for user {current_user.id}: {e!r}",
                    exc_info=True,
                )
                try:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": f"Internal error: {str(e)}",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                except Exception as send_error:
                    logger.error(
                        f"Failed to send error message to client {current_user.id}: {send_error!r}",
                        exc_info=True,
                    )
                    break

    finally:
        logger.info(f"Closing WebSocket connection for user {current_user.id}")
        db.close()


# =============================================================================
# Helper Functions
# =============================================================================


class ClaudeRateLimitError(Exception):
    """Raised when Claude API returns rate limit error."""

    pass


async def _stream_claude_response(
    api_key: str, messages: list[dict]
) -> AsyncIterator[dict]:
    """
    Stream Claude Code Agent SDK responses.

    This uses the Claude Agent SDK to stream responses with thoughts and outputs.
    """
    logger.debug(f"Initializing Claude Agent SDK stream with {len(messages)} messages")

    try:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            OutputBlock,
            TextBlock,
            ThinkingBlock,
            UserMessage,
            query,
        )
    except ImportError as e:
        logger.error(f"Claude Agent SDK not installed: {e!r}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Claude Agent SDK not installed",
        ) from e

    # Convert messages to SDK format
    sdk_messages = []
    for msg in messages:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            # Handle both string and content blocks
            if isinstance(content, str):
                sdk_messages.append(UserMessage(content=content))
            else:
                # Content blocks (for images, etc.)
                sdk_messages.append(UserMessage(content=content))

    # Configure options
    options = ClaudeAgentOptions(
        max_turns=10,
        env={"ANTHROPIC_API_KEY": api_key},
    )

    # Stream responses
    try:
        # For a simple chat, we just pass the last user message
        last_user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break

        if not last_user_message:
            logger.error("No user message found in messages list")
            raise ValueError("No user message found")

        logger.info(f"Starting Claude SDK query with message length: {len(str(last_user_message))}")

        message_count = 0
        async for message in query(prompt=last_user_message, options=options):
            timestamp = datetime.now(timezone.utc).isoformat()

            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ThinkingBlock):
                        message_count += 1
                        logger.debug(f"Yielding thought block #{message_count}")
                        yield {
                            "type": "thought",
                            "content": block.thinking,
                            "timestamp": timestamp,
                        }
                    elif isinstance(block, TextBlock):
                        message_count += 1
                        logger.debug(f"Yielding text block #{message_count}")
                        yield {
                            "type": "output",
                            "content": block.text,
                            "timestamp": timestamp,
                        }
                    elif isinstance(block, OutputBlock):
                        message_count += 1
                        logger.debug(f"Yielding output block #{message_count}")
                        yield {
                            "type": "output",
                            "content": block.output,
                            "timestamp": timestamp,
                        }

        logger.info(f"Claude SDK stream completed successfully with {message_count} message blocks")

    except Exception as e:
        error_str = str(e).lower()
        logger.error(f"Error in Claude SDK stream: {e!r}", exc_info=True)
        if "rate" in error_str and "limit" in error_str:
            raise ClaudeRateLimitError(str(e)) from e
        raise
