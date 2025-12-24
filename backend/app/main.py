import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import AuthMiddleware
from app.routers import (
    auth_router,
    comments_router,
    events_router,
    hats_router,
    jobs_router,
    plans_router,
    projects_router,
    sessions_router,
    system_router,
    tasks_router,
    triage_router,
    users_router,
)
from app.services.task_queue import close_redis_pool, get_redis_pool

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup/shutdown events."""
    # Startup
    logger.info("Initializing Redis connection pool...")
    await get_redis_pool()
    logger.info("Redis connection pool initialized")
    yield
    # Shutdown
    logger.info("Closing Redis connection pool...")
    await close_redis_pool()
    logger.info("Redis connection pool closed")


app = FastAPI(
    title="ATC API",
    description="Automated Team Collaboration API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(AuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROUTERS = [
    (auth_router, "Authentication"),
    (projects_router, "Projects"),
    (plans_router, "Plans"),
    (tasks_router, "Tasks"),
    (sessions_router, "Coding Sessions"),
    (comments_router, "Comments"),
    (users_router, "Users"),
    (hats_router, "HATs"),
    (triage_router, "Triage"),
    (system_router, "System"),
    (events_router, "Events"),
    (jobs_router, "Jobs"),
]

for router, tag in ROUTERS:
    app.include_router(router, prefix="/api/v1", tags=[tag])


@app.get("/health", tags=["Health"], include_in_schema=True)
async def health_check():
    return {"status": "healthy", "version": app.version}


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to ATC API", "docs": "/docs", "redoc": "/redoc"}
