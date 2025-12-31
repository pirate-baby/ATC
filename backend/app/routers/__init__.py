from app.routers.auth import router as auth_router
from app.routers.claude_tokens import router as claude_tokens_router
from app.routers.comments import router as comments_router
from app.routers.debug import router as debug_router
from app.routers.events import router as events_router
from app.routers.hats import router as hats_router
from app.routers.jobs import router as jobs_router
from app.routers.plans import router as plans_router
from app.routers.projects import router as projects_router
from app.routers.sessions import router as sessions_router
from app.routers.system import router as system_router
from app.routers.tasks import router as tasks_router
from app.routers.triage import router as triage_router
from app.routers.users import router as users_router

__all__ = [
    "auth_router",
    "claude_tokens_router",
    "projects_router",
    "plans_router",
    "tasks_router",
    "sessions_router",
    "comments_router",
    "users_router",
    "hats_router",
    "triage_router",
    "system_router",
    "events_router",
    "jobs_router",
    "debug_router",
]
