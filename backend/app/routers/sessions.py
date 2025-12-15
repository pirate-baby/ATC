from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status

from app.schemas import (
    CodingSession,
    CodingSessionStatus,
    PaginatedResponse,
    StandardError,
)

router = APIRouter()


@router.get(
    "/sessions",
    response_model=PaginatedResponse[CodingSession],
    summary="List coding sessions",
    description="Retrieve a paginated list of coding sessions with optional status filtering.",
    responses={401: {"model": StandardError, "description": "Unauthorized"}},
)
async def list_sessions(
    status: CodingSessionStatus | None = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    """List coding sessions."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/sessions/{session_id}",
    response_model=CodingSession,
    summary="Get session details",
    description="Retrieve details of a specific coding session.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Session not found"},
    },
)
async def get_session(session_id: UUID):
    """Get session details."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/sessions/{session_id}/abort",
    response_model=CodingSession,
    summary="Abort active session",
    description="Abort a running coding session. The associated plan/task moves to Review state.",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Session not found"},
        409: {"model": StandardError, "description": "Session is not running"},
    },
)
async def abort_session(session_id: UUID):
    """Abort an active session."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.websocket("/ws/sessions/{session_id}/stream")
async def session_stream(websocket: WebSocket, session_id: UUID):
    """
    WebSocket endpoint for bidirectional session streaming.

    Authentication: Pass JWT token as query parameter ?token={jwt}

    Server-to-Client messages:
    - output: {"type": "output", "content": "...", "timestamp": "..."}
    - status: {"type": "status", "status": "running|completed|aborted", "timestamp": "..."}
    - tool_use: {"type": "tool_use", "tool": "...", "input": {...}, "timestamp": "..."}

    Client-to-Server messages:
    - abort: {"type": "abort"}
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "abort":
                await websocket.send_json(
                    {"type": "status", "status": "aborted", "timestamp": "..."}
                )
                break
    except WebSocketDisconnect:
        pass
