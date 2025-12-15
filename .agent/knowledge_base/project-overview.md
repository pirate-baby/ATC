# ATC Project Overview

## What is ATC?

**Automated Team Collaboration (ATC)** is a software development lifecycle (SDLC) platform designed for the AI-enabled age. The name draws inspiration from Air Traffic Control—where software takes flight under human guidance.

## Project Mission

ATC redefines how software teams collaborate by integrating AI agents as first-class team members. The platform provides:

1. **Human-AI Collaboration**: Structured workflows where humans guide and AI agents execute
2. **Parallel Development**: Support for multiple concurrent feature branches with isolated environments
3. **Knowledge Management**: Centralized knowledge base accessible by AI agents during work sessions

## Core Features

### Multi-Worktree Support
Developers can have 2-6 concurrent branches checked out, each with:
- Isolated Docker services
- Automatic port allocation (no conflicts)
- Independent environments

### Dockerized Development
All services run in Docker containers for:
- Consistency across developer machines
- Easy onboarding
- Production-like local environments

### AI Agent Integration
Claude agents can:
- Access project knowledge through specialized subagents
- Query specific documents for accurate, contextual answers
- Maintain expertise without polluting primary context

## Project Status

ATC is in early development (bootstrap phase). The `.agent/` directory contains guidance for bootstrapping until the platform can manage itself.

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `.agent/` | Agent guidance, plans, tasks, and knowledge base |
| `backend/` | FastAPI Python application |
| `frontend/` | React TypeScript application |
| `dockerfiles/` | Container build definitions |
| `utils/` | Development utility scripts |

## Getting Started

1. Run `utils/startup.sh` to configure your environment
2. Run `docker compose up` to start all services
3. Access frontend at the port shown by startup script
