# ATC System Architecture

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL 16
- **ORM**: SQLAlchemy with async support (asyncpg)
- **Server**: Uvicorn with hot-reload in development

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: CSS (component-scoped)

### Infrastructure
- **Containerization**: Docker with Docker Compose
- **Reverse Proxy**: Nginx (optional, for production-like routing)
- **Database Volume**: Persistent local storage (`.data/pg_data`)

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Network                        │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ Frontend │───▶│  Nginx   │◀───│ Backend  │              │
│  │ (Vite)   │    │ (proxy)  │    │ (FastAPI)│              │
│  └──────────┘    └──────────┘    └──────────┘              │
│       │                               │                      │
│       │         ┌──────────┐          │                      │
│       └────────▶│    DB    │◀─────────┘                      │
│                 │(Postgres)│                                 │
│                 └──────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

## Port Offset System

To support multiple concurrent worktrees, ATC uses a port offset system:

| Offset | PostgreSQL | Backend | Frontend | Nginx |
|--------|------------|---------|----------|-------|
| 0      | 05432      | 08000   | 03000    | 080   |
| 1      | 15432      | 18000   | 13000    | 180   |
| 2      | 25432      | 28000   | 23000    | 280   |
| 3      | 35432      | 38000   | 33000    | 380   |
| 4      | 45432      | 48000   | 43000    | 480   |
| 5      | 55432      | 58000   | 53000    | 580   |

### How It Works
1. `utils/startup.sh` detects which offsets are in use by scanning Docker containers
2. It selects the lowest available offset (0-5)
3. Values are persisted to `.env` for `docker-compose`
4. `COMPOSE_PROJECT_NAME` is derived from the git branch name (sanitized)

## Docker Compose Profiles

| Profile | Service | Purpose |
|---------|---------|---------|
| (default) | db, backend, frontend, nginx | Core development services |
| test | test | Run pytest tests |
| lint | lint, frontend-lint | Code linting (ruff, eslint) |
| format | format, frontend-format | Code formatting |

## Directory Structure

```
atc/
├── .agent/                    # Agent guidance
│   ├── knowledge_base/        # Documents for agent context
│   ├── plans/                 # Strategic planning documents
│   └── tasks/                 # Execution specifications
├── backend/
│   ├── app/                   # FastAPI application
│   │   ├── __init__.py
│   │   └── main.py            # Application entry point
│   ├── tests/                 # Backend tests
│   └── pyproject.toml         # Python dependencies
├── frontend/
│   ├── src/                   # React source files
│   │   ├── App.tsx            # Main application component
│   │   └── main.tsx           # Entry point
│   ├── package.json           # Node dependencies
│   └── vite.config.ts         # Vite configuration
├── dockerfiles/
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
├── utils/
│   ├── startup.sh             # Environment configuration
│   └── stop.sh                # Cleanup script
└── docker-compose.yml         # Service definitions
```

## Design Decisions

### Why Docker for Everything?
- Consistent environments across all developer machines
- No "works on my machine" issues
- Easy cleanup and isolation between worktrees
- Simple onboarding for new developers

### Why Port Offsets Instead of Dynamic Ports?
- Predictable URLs for browser bookmarks and API clients
- Easier debugging when you know which port maps to which worktree
- Docker Compose doesn't support dynamic port allocation well

### Why Single Knowledge Base Agent?
- Scales to unlimited documents with zero maintenance
- No synchronization needed between agent files and documents
- Documents are read at runtime—always up to date
- Uses Haiku model for fast, cost-effective responses

## Health Checks

| Service | Endpoint | Check |
|---------|----------|-------|
| PostgreSQL | - | `pg_isready -U atc -d atc` |
| Backend | `/health` | HTTP 200 response |
| Frontend | - | Container running |

## Environment Variables

| Variable | Purpose | Set By |
|----------|---------|--------|
| `COMPOSE_PROJECT_NAME` | Docker resource labeling | startup.sh |
| `PORT_OFFSET` | Port prefix for all services | startup.sh |
| `DATABASE_URL` | PostgreSQL connection string | docker-compose.yml |
| `VITE_API_URL` | Backend URL for frontend | docker-compose.yml |
