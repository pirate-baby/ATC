"""Debug tools for Claude Code integration."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import RequireAuth, validate_websocket_token
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
    username: str
    email: str | None = None
    has_token: bool
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
                username=user.username,
                email=user.email,
                has_token=token is not None,
                token_name=token.name if token else None,
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
    current_user = await validate_websocket_token(websocket)
    if current_user is None:
        return

    await websocket.accept()

    db = next(iter(get_db()))
    try:
        await websocket.send_json(
            {"type": "status", "status": "connected", "timestamp": datetime.now(timezone.utc).isoformat()}
        )

        while True:
            try:
                data = await websocket.receive_json()

                if data.get("type") == "chat":
                    # Extract messages and optional token selection
                    messages = data.get("messages", [])
                    use_token_id = data.get("use_token_id")

                    if not messages:
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
                        token = db.scalar(
                            select(ClaudeTokenModel).where(ClaudeTokenModel.id == UUID(use_token_id))
                        )
                        if not token:
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
                        except ValueError as e:
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
                        token_result = await get_available_token(db)
                        if not token_result:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "error": "No available tokens in pool",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                            )
                            continue

                        token_str, token_id = token_result

                    # Stream Claude response
                    success = False
                    rate_limited = False
                    error_message = None

                    try:
                        async for message in _stream_claude_response(token_str, messages):
                            await websocket.send_json(message)

                        success = True
                        await websocket.send_json(
                            {"type": "done", "timestamp": datetime.now(timezone.utc).isoformat()}
                        )

                    except ClaudeRateLimitError as e:
                        rate_limited = True
                        error_message = str(e)
                        await websocket.send_json(
                            {
                                "type": "error",
                                "error": f"Rate limited: {str(e)}",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error streaming Claude response: {e}", exc_info=True)
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
                            await record_token_usage(
                                db=db,
                                token_id=token_id,
                                success=success,
                                rate_limited=rate_limited,
                                error_message=error_message,
                            )
                            db.commit()

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in debug console websocket: {e}", exc_info=True)
                try:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": f"Internal error: {str(e)}",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                except:
                    break

    finally:
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
        logger.error(f"Claude Agent SDK not installed: {e}")
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
            raise ValueError("No user message found")

        async for message in query(prompt=last_user_message, options=options):
            timestamp = datetime.now(timezone.utc).isoformat()

            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ThinkingBlock):
                        yield {
                            "type": "thought",
                            "content": block.thinking,
                            "timestamp": timestamp,
                        }
                    elif isinstance(block, TextBlock):
                        yield {
                            "type": "output",
                            "content": block.text,
                            "timestamp": timestamp,
                        }
                    elif isinstance(block, OutputBlock):
                        yield {
                            "type": "output",
                            "content": block.output,
                            "timestamp": timestamp,
                        }

    except Exception as e:
        error_str = str(e).lower()
        if "rate" in error_str and "limit" in error_str:
            raise ClaudeRateLimitError(str(e)) from e
        raise
