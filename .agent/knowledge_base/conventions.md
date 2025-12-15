# ATC Coding Conventions

## General Principles

1. **Simplicity First**: Prefer simple, readable code over clever solutions
2. **Explicit Over Implicit**: Make behavior obvious rather than relying on defaults
3. **Test-Driven**: Write tests before or alongside implementation
4. **Document Intent**: Comments explain "why", code explains "what"

## Python (Backend)

### Style
- Follow PEP 8 with 88-character line limit (Black/Ruff default)
- Use type hints for all function signatures
- Prefer `async/await` for I/O operations

### Naming
- `snake_case` for functions, variables, and modules
- `PascalCase` for classes
- `UPPER_SNAKE_CASE` for constants
- Prefix private attributes with underscore (`_private_method`)

### FastAPI Patterns
```python
# Endpoint naming: verb + resource
@app.get("/users")          # List users
@app.post("/users")         # Create user
@app.get("/users/{id}")     # Get specific user
@app.put("/users/{id}")     # Update user
@app.delete("/users/{id}")  # Delete user

# Use descriptive function names and typed parameters instead of docstrings
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Only use docstrings for non-obvious protocol documentation (WebSocket/SSE)
@app.websocket("/ws/sessions/{session_id}/stream")
async def session_stream(websocket: WebSocket, session_id: UUID):
    """
    Authentication: Pass JWT token as query parameter ?token={jwt}

    Server-to-Client messages:
    - output: {"type": "output", "content": "...", "timestamp": "..."}
    - status: {"type": "status", "status": "running|completed|aborted"}
    """
```

### Imports
```python
# Standard library
import os
from typing import Optional

# Third-party
from fastapi import FastAPI, HTTPException
from sqlalchemy import select

# Local
from app.models import User
from app.services import user_service
```

### Error Handling
```python
# Use HTTPException for API errors
raise HTTPException(status_code=404, detail="User not found")

# Use custom exceptions for business logic
class UserNotFoundError(Exception):
    pass
```

## TypeScript/React (Frontend)

### Style
- Use TypeScript strict mode
- Prefer functional components with hooks
- Use named exports (not default exports for components)

### Naming
- `camelCase` for variables, functions
- `PascalCase` for components, types, interfaces
- `UPPER_SNAKE_CASE` for constants
- Prefix interfaces with `I` only if there's a conflicting class

### Component Structure
```tsx
// Import order: react, third-party, local
import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { UserCard } from './UserCard'

// Props interface above component
interface UserListProps {
  filters?: string[]
}

// Named export
export function UserList({ filters }: UserListProps) {
  // Hooks first
  const [users, setUsers] = useState<User[]>([])

  // Effects
  useEffect(() => {
    // ...
  }, [])

  // Handlers
  const handleClick = () => {
    // ...
  }

  // Render
  return (
    <div>
      {users.map(user => (
        <UserCard key={user.id} user={user} />
      ))}
    </div>
  )
}
```

### State Management
- Local state: `useState` for component-specific state
- Shared state: React Context for app-wide state
- Server state: React Query for API data

## Docker

### Dockerfile Patterns
- Use multi-stage builds for production images
- Pin base image versions (e.g., `python:3.12-slim`)
- Order layers from least to most frequently changing
- Run as non-root user in production

### Docker Compose
- Use YAML anchors (`x-*`) for shared configuration
- Define health checks for all services
- Use profiles for optional services (test, lint, format)

## Git

### Branch Naming
- Feature: `feature/short-description`
- Bugfix: `fix/issue-description`
- For vibe-kanban: `vk/<task-id-prefix>-<short-description>`

### Commit Messages
- Use imperative mood: "Add feature" not "Added feature"
- Keep first line under 50 characters
- Add body for complex changes

## File Organization

### Backend
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app instance
│   ├── config.py        # Settings/configuration
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── routers/         # API route handlers
│   ├── services/        # Business logic
│   └── utils/           # Shared utilities
└── tests/
    ├── conftest.py      # Pytest fixtures
    ├── test_*.py        # Test files
    └── factories/       # Test data factories
```

### Frontend
```
frontend/
├── src/
│   ├── main.tsx         # Entry point
│   ├── App.tsx          # Root component
│   ├── components/      # Reusable components
│   ├── pages/           # Page components
│   ├── hooks/           # Custom hooks
│   ├── services/        # API clients
│   ├── types/           # TypeScript types
│   └── utils/           # Shared utilities
└── tests/
    └── *.test.tsx       # Component tests
```

## Testing

### Python
- Use pytest with async support
- Name test files `test_*.py`
- Name test functions `test_<what>_<expected>`
- Use factories for test data

### TypeScript
- Use Vitest for unit tests
- Use React Testing Library for component tests
- Test behavior, not implementation

## Linting & Formatting

| Tool | Language | Purpose |
|------|----------|---------|
| Ruff | Python | Linting and formatting |
| ESLint | TypeScript | Linting |
| Prettier | TypeScript | Formatting |

Run via Docker Compose profiles:
```bash
docker compose --profile lint up    # Run linters
docker compose --profile format up  # Run formatters
```
