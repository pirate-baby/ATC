import asyncio
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.auth import RequireAuth

router = APIRouter()


async def event_generator(project_id: UUID):
    yield "event: connected\ndata: {}\n\n"

    while True:
        await asyncio.sleep(30)
        yield "event: heartbeat\ndata: {}\n\n"


@router.get(
    "/events/projects/{project_id}",
    summary="Subscribe to project events",
    description="""
Subscribe to real-time events for a project using Server-Sent Events (SSE).

## Event Types

- **plan:created** - New plan created in project
- **plan:updated** - Plan content or status changed
- **task:created** - New task created in project
- **task:updated** - Task content or status changed
- **session:started** - Coding session started
- **session:ended** - Coding session ended
- **review:submitted** - New review submitted on plan or task
- **comment:added** - New comment added to a thread

Each event includes the full updated entity data in the `data` field.

## Example

```
event: task:updated
data: {"id": "...", "title": "...", "status": "coding", ...}

event: session:started
data: {"id": "...", "target_type": "task", "target_id": "...", ...}
```
    """,
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "SSE stream",
            "content": {"text/event-stream": {}},
        },
        401: {"description": "Unauthorized"},
        404: {"description": "Project not found"},
    },
)
async def subscribe_to_project_events(project_id: UUID, current_user: RequireAuth):
    return StreamingResponse(
        event_generator(project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
