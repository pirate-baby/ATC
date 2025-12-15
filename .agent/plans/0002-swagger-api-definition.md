# 0002: ATC Swagger API Definition

**Status**: Draft
**Author(s)**: Claude (AI Agent)
**Created**: 2025-12-15
**Updated**: 2025-12-15

## Summary

Define the complete OpenAPI/Swagger specification for ATC that serves as the master contract between frontend and backend teams. This API covers all core entities (Projects, Plans, Tasks, Users, HATs, Triage connections) and their interactions, including real-time streaming for agent output monitoring.

## Context

ATC is a team-based software development platform where AI agents execute work under human guidance. The frontend and backend teams will work in parallel, so a comprehensive Swagger API specification serves as the authoritative contract between them.

Key architectural considerations:
- All Plans and Tasks belong to a single Project (1:1 with git repository)
- Plans can spawn Tasks; complex Tasks can spawn sub-Plans (recursive hierarchy)
- Tasks form a DAG with blocking relationships (no circular dependencies)
- Real-time streaming is required for monitoring Claude Code agent sessions
- Multiple users collaborate with role-based review and approval workflows

## User Roles

### Frontend Developer
- Needs complete API documentation to build UI components
- Requires clear request/response schemas
- Needs real-time event specifications for live updates

### Backend Developer
- Needs clear endpoint contracts to implement
- Requires data model definitions
- Needs WebSocket/SSE specifications for streaming

### DevOps/Integration
- Needs authentication/authorization patterns
- Requires health check and status endpoints

## User Stories

### US-1: API Contract Discovery
As a frontend developer, I want to access a complete Swagger UI, so that I can explore all available endpoints and their schemas.

### US-2: Type Generation
As a frontend developer, I want to generate TypeScript types from the OpenAPI spec, so that I have compile-time safety when calling the API.

### US-3: Backend Implementation
As a backend developer, I want clear endpoint definitions, so that I know exactly what to implement.

### US-4: Real-time Integration
As a frontend developer, I want documented WebSocket/SSE endpoints, so that I can implement live agent output streaming.

## Goals

1. **Complete Coverage**: Document all CRUD operations for all entities
2. **Type Safety**: Provide detailed schemas for request/response bodies
3. **Real-time Specs**: Document streaming endpoints for live monitoring
4. **Relationship Clarity**: Document entity relationships and constraints
5. **Workflow Support**: Cover all state transitions and approval flows

## Non-Goals

- Implementation details (that's for task documents)
- Database schema design (separate concern)
- Authentication provider specifics (pluggable)
- Specific HAT implementations (defined in settings)

## Acceptance Criteria

### Core API Structure

**AC-1**: When the backend starts, the system shall expose an OpenAPI 3.1 specification at `/openapi.json`.

**AC-2**: When the backend starts, the system shall expose Swagger UI at `/docs`.

**AC-3**: When the backend starts, the system shall expose ReDoc at `/redoc`.

### Entity Endpoints

**AC-4**: The API shall provide complete CRUD endpoints for Projects, Plans, Tasks, Users, HATs, TriageConnections, and CommentThreads.

**AC-5**: The API shall enforce that all Plans and Tasks belong to exactly one Project.

**AC-6**: The API shall prevent circular dependencies in Task blocking relationships.

### Real-time Endpoints

**AC-7**: When a Task or Plan is in "Coding" state, the system shall provide a WebSocket endpoint for streaming agent output.

**AC-8**: The system shall provide SSE endpoints for state change notifications on watched entities.

### Workflow Endpoints

**AC-9**: The API shall provide endpoints for review actions (comment, approve, request changes).

**AC-10**: The API shall provide endpoints for aborting active coding sessions.

## Approach

### 1. API Versioning Strategy

Use URL-based versioning with all endpoints prefixed by `/api/v1/`. This allows breaking changes in future versions while maintaining backward compatibility.

### 2. Authentication Pattern

Bearer token authentication with JWT. All endpoints except health check require an Authorization header with a Bearer token. User context is derived from the JWT payload.

### 3. Entity Schemas

All schemas are defined in the OpenAPI `components/schemas` section with full JSON Schema validation. FastAPI automatically generates these from Pydantic models.

### 4. Streaming Strategy

- **WebSocket**: For bidirectional agent session streaming (view output, send abort signals)
- **SSE (Server-Sent Events)**: For unidirectional state change notifications

---

## Data Models

### Project

A Project maps 1:1 to a git repository.

**Required fields**: id (UUID), name (string), git_url (URI), main_branch (string, defaults to "main"), created_at (datetime)

**Optional fields**: settings (ProjectSettings object), triage_connection_id (UUID, nullable), updated_at (datetime)

The name is human-readable. The git_url is the repository URL. The main_branch specifies the primary branch name.

---

### ProjectSettings

Configuration for a project's workflow behavior.

**Fields**:
- required_approvals_plan: Integer (minimum 1, default 1) - Number of user approvals required before a Plan can be approved
- required_approvals_task: Integer (minimum 1, default 1) - Number of user approvals required before a Task moves to CI/CD
- auto_approve_main_updates: Boolean (default false) - When true, plans updated due to main branch changes skip re-review
- assigned_hats: Array of UUIDs - HAT IDs assigned to run on this project's coding sessions

---

### Plan

A Plan describes work to be done with context, reasoning, order of operations, considerations, and references. Plans focus on "what and why" rather than implementation specifics.

**Required fields**: id (UUID), project_id (UUID), title (string), status (PlanTaskStatus), created_at (datetime)

**Optional fields**:
- parent_task_id (UUID, nullable) - Set when this plan was spawned by a complex task that needed further breakdown
- content (string) - Markdown content describing the plan
- version (integer, default 1) - Incremented on each revision
- created_by (UUID) - User or system that created the plan
- updated_at (datetime)

---

### Task

A Task is an atomic unit of work to be executed by a Claude Code agent. Tasks describe "what and why" so the executing agent can design solutions based on the current codebase state.

**Required fields**: id (UUID), project_id (UUID), title (string), status (PlanTaskStatus), created_at (datetime)

**Optional fields**:
- plan_id (UUID, nullable) - Parent plan that spawned this task
- description (string) - What needs to be done and why
- blocked_by (array of UUIDs) - Task IDs that must complete before this task can start; forms a DAG (no circular dependencies allowed)
- branch_name (string, nullable) - Git branch name, created when task enters Coding state
- worktree_path (string, nullable) - Path to git worktree, created when task enters Coding state
- version (integer, default 1) - Incremented on each revision
- updated_at (datetime)

---

### PlanTaskStatus

A unified status enumeration used by both Plans and Tasks. The valid values are:

- **backlog**: Not yet started, waiting to be picked up
- **blocked**: Cannot proceed because upstream dependencies (blocking tasks) haven't completed
- **coding**: Claude Code agent is actively working on this item
- **review**: Work complete, awaiting human review
- **approved**: Humans have approved; for tasks, pending CI/CD or merge
- **cicd**: Running in CI/CD pipeline
- **merged**: Successfully merged to main branch
- **closed**: Completed or cancelled

Items automatically transition from backlog/blocked to coding when workers are available and blockers are resolved.

---

### User

A User is a human with a git handle who collaborates on projects.

**Required fields**: id (UUID), git_handle (string), email (email format)

**Optional fields**: display_name (string), avatar_url (URI, nullable), created_at (datetime)

The git_handle is the user's GitHub/GitLab username.

---

### HAT (Heightened Ability Template)

A HAT defines a specific, abstract process for improving code that runs after the initial Claude Code session ends. HATs handle concerns like style, architecture, naming, and other quality improvements before humans review the work.

**Required fields**: id (UUID), name (string), type (enum)

**Optional fields**: description (string), definition (string - the actual command/skill/agent content), enabled (boolean, default true), created_at (datetime)

**Type values**: slash_command, skill, subagent

HATs are defined globally in ATC settings and assigned to specific projects.

---

### TriageConnection

A connection to an external issue tracker for importing work items. Supports Linear, GitHub Issues, Jira, and GitLab Issues.

**Required fields**: id (UUID), provider (enum), name (string)

**Optional fields**: config (object - provider-specific configuration), last_sync_at (datetime, nullable), created_at (datetime)

**Provider values**: linear, github_issues, jira, gitlab_issues

New work from triage connections is automatically planned and moved to Review state.

---

### TriageItem

An issue or ticket imported from a triage connection, pending planning.

**Required fields**: id (UUID), connection_id (UUID), external_id (string), title (string)

**Optional fields**: external_url (URI), description (string, nullable), plan_id (UUID, nullable - set when a plan is created from this item), status (enum, default "pending"), imported_at (datetime)

**Status values**: pending (awaiting planning), planned (plan created), rejected (not suitable for ATC)

---

### CommentThread

A threaded discussion attached to a plan, task, or specific line of code. Users can comment on each other's comments within threads.

**Required fields**: id (UUID), target_type (enum), target_id (UUID)

**Optional fields**:
- file_path (string, nullable) - For code_line comments
- line_number (integer, nullable) - For code_line comments
- status (enum, default "open")
- summary (string, nullable) - AI-generated summary of the final decision
- created_at (datetime)

**Target type values**: plan, task, code_line

**Status values**: open, resolved, summarized

When a thread is resolved, a subprocess reviews the thread content in context and generates a summarized final decision for inclusion in the main context.

---

### Comment

An individual comment within a thread.

**Required fields**: id (UUID), thread_id (UUID), author_id (UUID), content (string)

**Optional fields**: parent_comment_id (UUID, nullable - for replying to specific comments), created_at (datetime), updated_at (datetime)

---

### CodingSession

Represents an active or completed Claude Code agent session working on a Plan or Task.

**Required fields**: id (UUID), target_type (enum), target_id (UUID), status (enum)

**Optional fields**: started_at (datetime), ended_at (datetime, nullable), output_log (string - full session output stored after completion)

**Target type values**: plan, task

**Status values**: running, completed, aborted

When a session completes (or is aborted), the associated Plan/Task moves to Review state.

---

### Review

A review action submitted by a user on a Plan or Task in Review state.

**Required fields**: id (UUID), target_type (enum), target_id (UUID), reviewer_id (UUID), decision (enum)

**Optional fields**: comment (string, nullable), created_at (datetime)

**Target type values**: plan, task

**Decision values**: approved, request_changes, comment_only

Approving a Plan triggers automatic Task creation. Approving a Task pushes it to CI/CD state. Project settings may require multiple approvals.

---

### CodeDiff

The git diff of changes made by a task compared to the base branch.

**Fields**:
- base_branch (string)
- head_branch (string)
- files (array of file diff objects)

Each file diff contains: path (string), status (added/modified/deleted/renamed), additions (integer), deletions (integer), patch (string in unified diff format)

---

## API Endpoints

### Projects

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/projects | List all projects with pagination |
| POST | /api/v1/projects | Create a new project |
| GET | /api/v1/projects/{project_id} | Get project by ID |
| PATCH | /api/v1/projects/{project_id} | Update project |
| DELETE | /api/v1/projects/{project_id} | Delete project |
| GET | /api/v1/projects/{project_id}/settings | Get project settings |
| PATCH | /api/v1/projects/{project_id}/settings | Update project settings |

---

### Plans

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/projects/{project_id}/plans | List plans in project with status filter and pagination |
| POST | /api/v1/projects/{project_id}/plans | Create a new plan |
| GET | /api/v1/plans/{plan_id} | Get plan with full details (tasks, reviews, threads) |
| PATCH | /api/v1/plans/{plan_id} | Update plan |
| DELETE | /api/v1/plans/{plan_id} | Delete plan |
| GET | /api/v1/plans/{plan_id}/tasks | List tasks spawned by this plan |
| GET | /api/v1/plans/{plan_id}/reviews | List reviews for this plan |
| POST | /api/v1/plans/{plan_id}/reviews | Submit a review for this plan |
| POST | /api/v1/plans/{plan_id}/approve | Approve plan (creates tasks automatically) |

The approve endpoint returns 409 Conflict if insufficient approvals or plan not in review state.

---

### Tasks

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/projects/{project_id}/tasks | List tasks in project with status filter and pagination |
| GET | /api/v1/tasks/{task_id} | Get task with full details (plan, blocking tasks, reviews, threads, active session) |
| PATCH | /api/v1/tasks/{task_id} | Update task |
| DELETE | /api/v1/tasks/{task_id} | Delete task |
| GET | /api/v1/tasks/{task_id}/blocking | Get tasks that block this task |
| PUT | /api/v1/tasks/{task_id}/blocking | Set blocking tasks (validates no circular dependencies) |
| GET | /api/v1/tasks/{task_id}/reviews | List reviews for this task |
| POST | /api/v1/tasks/{task_id}/reviews | Submit a review for this task |
| POST | /api/v1/tasks/{task_id}/approve | Approve task (pushes to CI/CD) |
| POST | /api/v1/tasks/{task_id}/spawn-plan | Spawn a sub-plan from complex task |
| GET | /api/v1/tasks/{task_id}/diff | Get code diff for task |

The blocking endpoint returns 409 Conflict if a circular dependency would be created. The approve endpoint returns 409 if insufficient approvals or task not in review state.

---

### Coding Sessions

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/sessions | List sessions with status filter and pagination |
| GET | /api/v1/sessions/{session_id} | Get session details |
| POST | /api/v1/sessions/{session_id}/abort | Abort an active session (pushes item to Review) |

The abort endpoint returns 409 Conflict if session is not running.

---

### Comment Threads

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/plans/{plan_id}/threads | List comment threads on a plan |
| POST | /api/v1/plans/{plan_id}/threads | Create a comment thread on a plan |
| GET | /api/v1/tasks/{task_id}/threads | List comment threads on a task (filter by type: task or code_line) |
| POST | /api/v1/tasks/{task_id}/threads | Create a comment thread on a task or code line |
| GET | /api/v1/threads/{thread_id} | Get thread with all comments |
| POST | /api/v1/threads/{thread_id}/resolve | Resolve a thread (triggers AI summarization) |
| GET | /api/v1/threads/{thread_id}/comments | List comments in thread |
| POST | /api/v1/threads/{thread_id}/comments | Add comment to thread |

---

### Users

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/users | List users with pagination |
| GET | /api/v1/users/me | Get current authenticated user |
| GET | /api/v1/users/{user_id} | Get user by ID |

---

### HATs (Heightened Ability Templates)

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/hats | List all HATs with type filter and pagination |
| POST | /api/v1/hats | Create a new HAT |
| GET | /api/v1/hats/{hat_id} | Get HAT by ID |
| PATCH | /api/v1/hats/{hat_id} | Update HAT |
| DELETE | /api/v1/hats/{hat_id} | Delete HAT |

---

### Triage Connections

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/triage-connections | List triage connections |
| POST | /api/v1/triage-connections | Create triage connection |
| GET | /api/v1/triage-connections/{connection_id} | Get connection details |
| PATCH | /api/v1/triage-connections/{connection_id} | Update connection |
| DELETE | /api/v1/triage-connections/{connection_id} | Delete connection |
| POST | /api/v1/triage-connections/{connection_id}/sync | Trigger manual sync (returns sync_id) |
| GET | /api/v1/triage-connections/{connection_id}/items | List imported triage items with status filter |
| POST | /api/v1/triage-items/{item_id}/plan | Create a plan from triage item (requires project_id) |
| POST | /api/v1/triage-items/{item_id}/reject | Reject triage item (optional reason) |

---

### Health & System

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check (returns status and version) |
| GET | /api/v1/system/stats | System statistics (active sessions, pending reviews, tasks in progress) |

---

## Real-time Endpoints

### WebSocket: Session Streaming

**Endpoint**: /ws/sessions/{session_id}/stream

**Authentication**: Pass JWT token as query parameter: ?token={jwt}

**Purpose**: Bidirectional streaming for active Claude Code sessions. Users can view real-time output and send abort signals.

**Server-to-Client Message Types**:
- **output**: Contains content string and timestamp - streaming text output from the agent
- **status**: Contains status (running/completed/aborted) and timestamp - session state changes
- **tool_use**: Contains tool name, input object, and timestamp - when agent uses a tool

**Client-to-Server Message Types**:
- **abort**: Signals the server to abort the running session

---

### SSE: Entity Updates

**Endpoint**: GET /api/v1/events/projects/{project_id}

**Purpose**: Server-Sent Events stream for real-time updates on project activity. Unidirectional from server to client.

**Event Types**:
- plan:created - New plan created in project
- plan:updated - Plan content or status changed
- task:created - New task created in project
- task:updated - Task content or status changed
- session:started - Coding session started
- session:ended - Coding session ended
- review:submitted - New review submitted on plan or task
- comment:added - New comment added to a thread

Each event includes the full updated entity data.

---

## Common Parameters

### Path Parameters

All entity IDs (project_id, plan_id, task_id, session_id, thread_id, user_id, hat_id, connection_id, item_id) are UUIDs.

### Query Parameters

- **page**: Integer, minimum 1, default 1 - Page number for pagination
- **limit**: Integer, minimum 1, maximum 100, default 20 - Items per page
- **status**: PlanTaskStatus enum value - Filter by status

---

## Error Responses

### Standard Error

All errors return an object with: error (string code), message (human-readable description), and optional details object.

### Validation Error

Validation failures return: error set to "validation_error", message, and fields array where each field object contains field name and error message.

### Common HTTP Status Codes

- 200: Success
- 201: Created
- 204: Deleted (no content)
- 400: Bad request / Validation error
- 401: Unauthorized (authentication required)
- 404: Resource not found
- 409: Conflict (circular dependency, insufficient approvals, wrong state)

---

## Security

All endpoints except /health require Bearer token authentication. The OpenAPI spec defines a bearerAuth security scheme using HTTP bearer with JWT format.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| API drift between frontend/backend | High | Use OpenAPI codegen for types; CI validation |
| WebSocket connection stability | Medium | Implement reconnection logic; heartbeat pings |
| Circular dependency in task blocking | High | Server-side DAG validation on every update |
| Large diff payloads | Medium | Pagination; streaming for large diffs |
| Stale data in UI | Medium | SSE for real-time updates; optimistic UI |

## Implementation Tasks

The following tasks should be created to implement this API:

1. **Task: Create OpenAPI Base Configuration**
   - Set up FastAPI automatic OpenAPI generation
   - Configure Swagger UI and ReDoc
   - Define global security scheme

2. **Task: Implement Project Endpoints**
   - CRUD operations for Projects
   - Project settings management

3. **Task: Implement Plan Endpoints**
   - CRUD operations for Plans
   - Review submission and approval workflow
   - Plan-to-Task spawning

4. **Task: Implement Task Endpoints**
   - CRUD operations for Tasks
   - Blocking relationship management with DAG validation
   - Task approval workflow
   - Code diff retrieval

5. **Task: Implement Session Endpoints**
   - Session listing and details
   - Session abort functionality
   - WebSocket streaming endpoint

6. **Task: Implement Comment System**
   - Thread CRUD operations
   - Comment CRUD operations
   - Thread resolution with AI summarization

7. **Task: Implement HAT Management**
   - HAT CRUD operations
   - HAT assignment to projects

8. **Task: Implement Triage System**
   - Connection management
   - Item listing and filtering
   - Plan creation from triage items

9. **Task: Implement SSE Event System**
   - Project-level event streaming
   - Event type definitions
   - Connection management

10. **Task: Generate Frontend TypeScript Types**
    - Set up openapi-typescript-codegen
    - Create CI job for type generation
    - Document type usage patterns

## References

- OpenAPI 3.1 Specification
- FastAPI OpenAPI Support documentation
- WebSocket Protocol (RFC 6455)
- Server-Sent Events (HTML Living Standard)
- Plan 0001: Basic Repository Structure
