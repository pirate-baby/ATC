from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import AuthMiddleware
from app.routers import (
    comments_router,
    events_router,
    hats_router,
    plans_router,
    projects_router,
    sessions_router,
    system_router,
    tasks_router,
    triage_router,
    users_router,
)

app = FastAPI(
    title="ATC API",
    description="Automated Team Collaboration API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Authentication middleware - enforces JWT auth on all routes except public ones
app.add_middleware(AuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROUTERS = [
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
]

for router, tag in ROUTERS:
    app.include_router(router, prefix="/api/v1", tags=[tag])


@app.get("/health", tags=["Health"], include_in_schema=True)
async def health_check():
    return {"status": "healthy", "version": app.version}


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to ATC API", "docs": "/docs", "redoc": "/redoc"}
