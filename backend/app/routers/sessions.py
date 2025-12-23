from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import validate_websocket_token
from app.database import get_db, get_or_404
from app.models.coding_session import CodingSession as CodingSessionModel
from app.models.enums import PlanTaskStatus
from app.models.plan import Plan
from app.models.task import Task
from app.schemas import (
    CodingSession,
    CodingSessionStatus,
    PaginatedResponse,
    StandardError,
)
from app.schemas.session import SessionTargetType
from app.schemas.websocket import StatusMessage

router = APIRouter()


@router.get(
    "/sessions",
    response_model=PaginatedResponse[CodingSession],
    summary="List coding sessions",
    description="Retrieve a paginated list of coding sessions with optional status filtering.",
    responses={401: {"model": StandardError, "description": "Unauthorized"}},
)
async def list_sessions(
    status_filter: CodingSessionStatus | None = Query(
        default=None, alias="status", description="Filter by status"
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    query = select(CodingSessionModel)
    if status_filter is not None:
        query = query.where(CodingSessionModel.status == status_filter.value)
    query = query.order_by(CodingSessionModel.started_at.desc())

    all_sessions = list(db.scalars(query).all())
    total = len(all_sessions)
    offset = (page - 1) * limit
    items = all_sessions[offset : offset + limit]
    pages = (total + limit - 1) // limit if total > 0 else 0

    return PaginatedResponse[CodingSession](
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


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
async def get_session(session_id: UUID, db: Session = Depends(get_db)):
    session = get_or_404(db, CodingSessionModel, session_id, "Session not found")
    return session


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
async def abort_session(session_id: UUID, db: Session = Depends(get_db)):
    session = get_or_404(db, CodingSessionModel, session_id, "Session not found")

    if session.status != CodingSessionStatus.RUNNING.value:
        raise HTTPException(status_code=409, detail="Session is not running")

    session.status = CodingSessionStatus.ABORTED.value
    session.ended_at = datetime.now(timezone.utc)

    # Update the target (plan or task) status to REVIEW
    if session.target_type == SessionTargetType.PLAN.value:
        target = db.scalar(select(Plan).where(Plan.id == session.target_id))
        if target:
            target.status = PlanTaskStatus.REVIEW
    elif session.target_type == SessionTargetType.TASK.value:
        target = db.scalar(select(Task).where(Task.id == session.target_id))
        if target:
            target.status = PlanTaskStatus.REVIEW

    db.flush()
    return session


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
    current_user = await validate_websocket_token(websocket)
    if current_user is None:
        return

    # Validate session exists and is running
    db = next(iter(get_db()))
    try:
        session = db.scalar(select(CodingSessionModel).where(CodingSessionModel.id == session_id))

        if session is None:
            await websocket.close(code=4004, reason="Session not found")
            return

        if session.status != CodingSessionStatus.RUNNING.value:
            await websocket.close(code=4009, reason="Session is not running")
            return

        await websocket.accept()

        # Send initial status message
        await websocket.send_json(
            StatusMessage(status=session.status, timestamp=datetime.now(timezone.utc)).model_dump(
                mode="json"
            )
        )

        try:
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "abort":
                    # Abort the session
                    session.status = CodingSessionStatus.ABORTED.value
                    session.ended_at = datetime.now(timezone.utc)

                    # Update target status to REVIEW
                    if session.target_type == SessionTargetType.PLAN.value:
                        target = db.scalar(select(Plan).where(Plan.id == session.target_id))
                        if target:
                            target.status = PlanTaskStatus.REVIEW
                    elif session.target_type == SessionTargetType.TASK.value:
                        target = db.scalar(select(Task).where(Task.id == session.target_id))
                        if target:
                            target.status = PlanTaskStatus.REVIEW

                    db.commit()

                    await websocket.send_json(
                        StatusMessage(
                            status=CodingSessionStatus.ABORTED.value,
                            timestamp=datetime.now(timezone.utc),
                        ).model_dump(mode="json")
                    )
                    break
        except WebSocketDisconnect:
            pass
    finally:
        db.close()
