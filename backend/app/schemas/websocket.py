from datetime import datetime
from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field


class WSServerMessageType(str, Enum):
    OUTPUT = "output"
    STATUS = "status"
    TOOL_USE = "tool_use"


class WSClientMessageType(str, Enum):
    ABORT = "abort"


class OutputMessage(BaseModel):
    type: Literal["output"] = "output"
    content: str = Field(description="Output text content")
    timestamp: datetime = Field(description="Message timestamp")


class StatusMessage(BaseModel):
    type: Literal["status"] = "status"
    status: str = Field(description="Session status (running/completed/aborted)")
    timestamp: datetime = Field(description="Message timestamp")


class ToolUseMessage(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    tool: str = Field(description="Tool name")
    input: dict = Field(description="Tool input parameters")
    timestamp: datetime = Field(description="Message timestamp")


class AbortMessage(BaseModel):
    type: Literal["abort"] = "abort"


WSServerMessage = Union[OutputMessage, StatusMessage, ToolUseMessage]
WSClientMessage = AbortMessage
