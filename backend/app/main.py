import logging
import sys
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth import AuthMiddleware
from app.config import settings
from app.routers import (
    auth_router,
    claude_tokens_router,
    comments_router,
    debug_router,
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


def configure_logging():
    """Configure application-wide logging with proper formatting."""
    log_level = logging.DEBUG if settings.environment == "development" else logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,  # Override any existing configuration
    )

    # Set specific log levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured at {logging.getLevelName(log_level)} level")
    return logger


logger = configure_logging()


def run_migrations() -> None:
    """Run database migrations using Alembic."""
    # Find the alembic.ini file relative to the backend directory
    backend_dir = Path(__file__).parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"

    if not alembic_ini_path.exists():
        logger.warning(f"alembic.ini not found at {alembic_ini_path}, skipping migrations")
        return

    alembic_cfg = Config(str(alembic_ini_path))
    # Set the script location relative to the alembic.ini file
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    # Set the database URL from settings
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

    logger.info("Running database migrations...")
    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations completed successfully")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup/shutdown events."""
    # Startup
    # Run database migrations first
    run_migrations()

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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to catch and log all unhandled exceptions."""
    # Log the full exception with traceback
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}: {exc!r}",
        exc_info=True,
        extra={
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else None,
            "exception_type": type(exc).__name__,
        },
    )

    # Return JSON error response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.environment == "development" else "An unexpected error occurred",
            "type": type(exc).__name__,
        },
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses."""
    logger.info(f"→ {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        log_level = logging.ERROR if response.status_code >= 400 else logging.INFO
        logger.log(log_level, f"← {request.method} {request.url.path} → {response.status_code}")
        return response
    except Exception as e:
        logger.error(
            f"← {request.method} {request.url.path} → EXCEPTION: {e!r}",
            exc_info=True,
        )
        raise


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
    (claude_tokens_router, "Claude Tokens"),
    (system_router, "System"),
    (events_router, "Events"),
    (jobs_router, "Jobs"),
    (debug_router, "Debug"),
]

for router, tag in ROUTERS:
    app.include_router(router, prefix="/api/v1", tags=[tag])


@app.get("/health", tags=["Health"], include_in_schema=True)
async def health_check():
    return {"status": "healthy", "version": app.version}


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to ATC API", "docs": "/docs", "redoc": "/redoc"}
