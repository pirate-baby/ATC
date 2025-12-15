from datetime import datetime
from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field


class WSServerMessageType(str, Enum):
    """Server-to-client message types."""

    OUTPUT = "output"
    STATUS = "status"
    TOOL_USE = "tool_use"


class WSClientMessageType(str, Enum):
    """Client-to-server message types."""

    ABORT = "abort"


class OutputMessage(BaseModel):
    """Streaming text output from the agent."""

    type: Literal["output"] = "output"
    content: str = Field(description="Output text content")
    timestamp: datetime = Field(description="Message timestamp")


class StatusMessage(BaseModel):
    """Session state change notification."""

    type: Literal["status"] = "status"
    status: str = Field(description="Session status (running/completed/aborted)")
    timestamp: datetime = Field(description="Message timestamp")


class ToolUseMessage(BaseModel):
    """Notification when agent uses a tool."""

    type: Literal["tool_use"] = "tool_use"
    tool: str = Field(description="Tool name")
    input: dict = Field(description="Tool input parameters")
    timestamp: datetime = Field(description="Message timestamp")


class AbortMessage(BaseModel):
    """Client request to abort the session."""

    type: Literal["abort"] = "abort"


# Union types for message handling
WSServerMessage = Union[OutputMessage, StatusMessage, ToolUseMessage]
WSClientMessage = AbortMessage
