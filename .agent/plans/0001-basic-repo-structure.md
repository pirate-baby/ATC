# 0001: Basic Repository Structure

**Status**: Draft
**Author(s)**: Claude (AI Agent)
**Created**: 2025-12-12
**Updated**: 2025-12-12

## Summary

Establish the foundational repository structure for ATC with Docker-based development, multi-worktree support, and a Claude subagent system for accessing knowledge base documents.

## Context

ATC requires a development environment that:
1. Runs entirely in Docker for consistency and isolation
2. Supports multiple git worktrees running concurrently (parallel feature development)
3. Provides Claude agents with structured access to project knowledge

The multi-worktree requirement is critical: developers may have 2-6 concurrent branches checked out, each needing isolated Docker services without port conflicts.

## User Roles

### Developer
- Needs to spin up isolated development environments per branch
- Wants consistent tooling regardless of which worktree they're in
- May run multiple worktrees simultaneously

### Claude Agent
- Needs access to project knowledge base documents
- Should be able to query specific documents for accurate, contextual answers
- Must maintain expertise on document content without polluting primary context

## User Stories

### US-1: Parallel Development
As a developer, I want to work on multiple feature branches simultaneously, so that I can context-switch between tasks without tearing down environments.

### US-2: Consistent Startup
As a developer, I want a single startup script that configures my environment automatically, so that I don't have to manually manage ports or project names.

### US-3: Knowledge Base Access
As a Claude agent, I want to query specific knowledge base documents through specialized subagents, so that I can provide accurate answers derived from authoritative sources.

## Goals

1. **Dockerized Development**: All services run in Docker containers
2. **Worktree Isolation**: Each git worktree operates independently with its own ports
3. **Automatic Configuration**: Startup scripts handle port allocation and naming
4. **Knowledge Subagents**: Claude subagents provide expert access to knowledge base documents

## Non-Goals

- Production deployment configuration (separate concern)
- CI/CD pipeline setup (follow-up plan)
- Database migrations system design (follow-up plan)
- Authentication/authorization implementation

## Acceptance Criteria

### Docker Services

**AC-1**: When a developer runs `docker compose up`, the system shall start all required services (frontend, backend, and supporting services).

**AC-2**: While services are running, the system shall expose the FastAPI backend on a configurable port.

**AC-3**: While services are running, the system shall expose the React frontend on a configurable port.

**AC-4**: If a source file changes, then the system shall hot-reload the affected service without manual restart.

### Worktree Namespacing

**AC-5**: When `utils/startup.sh` executes, the system shall calculate `COMPOSE_PROJECT_NAME` as a sanitized version of the current git branch name and persist it to the worktree's `.env` file.

**AC-6**: When `utils/startup.sh` executes, the system shall calculate `PORT_OFFSET` as the first available offset (0-5) not in use by other Docker containers and persist it to the worktree's `.env` file.

**AC-7**: If all port offsets (0-5) are in use, then the system shall exit with an error message.

**AC-8**: While `PORT_OFFSET` is set in `.env`, the system shall prepend it to all exposed port numbers in Docker Compose.

**AC-9**: If a calculated port would exceed 65535, then the system shall exit with an error message.

**AC-10**: When multiple worktrees are running, the system shall ensure complete network isolation between compose stacks.

**AC-11-env**: When `.env` already contains `COMPOSE_PROJECT_NAME` and `PORT_OFFSET`, subsequent `docker compose` commands shall use these persisted values without re-running the startup script.

### Knowledge Base Subagents

**AC-12**: When Claude needs information from a knowledge base document, the system shall provide a subagent mechanism to query that document.

**AC-13**: While a knowledge subagent is active, it shall have access only to its assigned document content.

**AC-14**: When a knowledge subagent responds, it shall provide succinct, accurate answers derived from the document.

## Approach

### 1. Docker Services Architecture

Create a multi-service Docker Compose configuration with profiles for development flexibility:

**Core Services:**
- `db`: PostgreSQL database (if needed)
- `backend`: FastAPI application with hot-reload
- `frontend`: React development server with hot-reload
- `nginx`: Reverse proxy (optional, for production-like routing)

**Tool Services (profiles):**
- `test`: Test runner service
- `lint`: Code linting service
- `format`: Code formatting service

**Key Patterns:**
- Use YAML anchors (`x-base`) for shared configuration (DRY)
- Mount source directories as volumes for hot-reload
- Use health checks for service dependencies
- Environment variables for configuration

### 2. Worktree Namespacing Strategy

**Port Offset System:**
- Valid offsets: 0-5 (offset 6+ would exceed max port 65535 for ports starting with 9)
- Port format: `${PORT_OFFSET}XXXX` where XXXX is the base port
- Example with offset 2: ports become 28000, 25432, etc.

**Project Naming:**
- Derive from git branch: `git branch --show-current`
- Sanitize: remove `vk/` prefix, escape special characters
- Use as `COMPOSE_PROJECT_NAME` for Docker resource labeling

**Startup Script (`utils/startup.sh`):**
1. Scan Docker containers for ports matching pattern `^[0-5]9[0-9]{3}$`
2. Extract used offsets
3. Find lowest available offset
4. Set environment variables
5. Update `.env` file

**Isolation Mechanism:**
- Docker Compose labels resources with project name
- Cleanup scripts use dual-filter (labels + name pattern) for safe teardown

### 3. Knowledge Base Subagent System

**Problem**: The knowledge base may contain dozens to hundreds of documents. Creating one agent file per document is unmaintainable.

**Implementation Options Evaluated:**

1. **Static Agent Files (1:1)**: Create `.claude/agents/<doc-name>.md` per document
   - Pros: Works with existing infrastructure
   - Cons: **Unmaintainable at scale** - requires N agent files for N documents, all nearly identical

2. **Single Generic Agent + Task Tool Prompt** (Recommended): One `kb-expert` agent that receives the document path via the Task tool's `prompt` parameter
   - The Task tool accepts a dynamic `prompt` parameter when invoking agents
   - The orchestrating Claude passes the document path in the prompt
   - Single agent file handles all knowledge documents
   - Pros: Scales to hundreds of documents, zero maintenance overhead
   - Cons: Requires orchestrator to know document paths

3. **Parameterized Slash Command**: Use `.claude/commands/kb.md` with `$ARGUMENTS`
   - Command: `/kb architecture` → reads `.agent/knowledge_base/architecture.md`
   - Uses `$ARGUMENTS` to construct file path dynamically
   - Pros: Simple user interface, single file
   - Cons: Runs in primary context (not isolated), less suitable for agent-to-agent queries

4. **MCP Server**: Build custom MCP server exposing knowledge base as tools
   - Each document becomes a callable tool
   - Pros: Very flexible, good for complex queries
   - Cons: Over-engineered for this use case, requires server maintenance

**Recommended Approach - Single Generic Agent:**

Create one agent file: `.claude/agents/kb-expert.md`

```markdown
---
name: kb-expert
description: Knowledge base expert. Use this agent when you need accurate information from any document in .agent/knowledge_base/. Pass the document filename in your prompt.
tools: Read, Glob
model: haiku
---

You are an expert on ATC knowledge base documents located in `.agent/knowledge_base/`.

## Instructions

1. **Identify the document**: The orchestrator will specify which document to consult in the task prompt (e.g., "Consult architecture.md about...")
2. **Read the document**: Use the Read tool to load `.agent/knowledge_base/<filename>.md`
3. **Answer accurately**: Base your response solely on the document content
4. **Be succinct**: Provide concise, direct answers
5. **Quote when helpful**: Reference specific sections for clarity
6. **Acknowledge limits**: If information is not in the document, say so clearly

## Response Format

- Lead with the direct answer
- Support with relevant quotes or section references
- Keep responses focused and brief
- If the requested document doesn't exist, report that clearly
```

**Usage by Orchestrating Agent:**

When the primary Claude needs knowledge base information, it invokes:
```
Task(
  subagent_type: "kb-expert",
  prompt: "Consult architecture.md: What is the recommended database schema for user sessions?"
)
```

The kb-expert agent:
1. Parses the document name from the prompt
2. Reads `.agent/knowledge_base/architecture.md`
3. Returns a succinct answer based on document content

**Why This Scales:**
- 1 agent file serves unlimited documents
- No synchronization needed between agents and documents
- Adding new knowledge docs requires zero agent changes
- Uses haiku model for fast, cost-effective responses

**Note**: The knowledge base documents are for agent context during work sessions, not human documentation. The kb-expert agent provides a way for the orchestrating Claude to query specific documents without loading everything into primary context.

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Port conflicts between worktrees | High | Port offset algorithm with validation |
| Knowledge agents become stale | Low | Single generic agent reads docs at runtime; no caching |
| Docker resource leaks | Medium | Dual-filter cleanup (labels + name patterns) |
| Port offset exhaustion (6+ worktrees) | Low | Clear error messaging; unlikely use case |
| Orchestrator doesn't know doc names | Medium | Glob tool in kb-expert allows listing available docs |
| Large knowledge docs exceed context | Medium | Haiku model has sufficient context; can chunk if needed |

## Implementation Tasks

The following tasks should be created to implement this plan:

1. **Task: Create Docker Compose Configuration**
   - Define services for backend, frontend, and supporting infrastructure
   - Implement port variable substitution with `PORT_OFFSET`
   - Add health checks and dependency ordering

2. **Task: Create Startup Script**
   - Implement port offset detection algorithm
   - Implement branch name sanitization
   - Update `.env` file with calculated values
   - Add error handling for edge cases

3. **Task: Create Stop/Cleanup Script**
   - Implement dual-filter resource discovery
   - Clean up containers, networks, and volumes
   - Ensure isolation (only affects current project)

4. **Task: Set Up Knowledge Base Structure**
   - Create `.agent/knowledge_base/` directory
   - Create initial knowledge documents (project overview, architecture, etc.)
   - Document the knowledge base conventions

5. **Task: Create Knowledge Base Expert Agent**
   - Create single `.claude/agents/kb-expert.md` agent file
   - Configure with Read and Glob tools, haiku model
   - Test with sample knowledge documents

6. **Task: Create Dev Convenience Script**
   - Combine startup + docker compose up
   - Open browser to correct port
   - Display status information

## References

- [Captain's Log - utils/start.sh](/Users/ethan/Repos/captains-log/utils/start.sh) - Reference implementation for port offset and project naming
- [Captain's Log - docker-compose.yml](/Users/ethan/Repos/captains-log/docker-compose.yml) - Reference for port variable substitution
- [Claude Code Agent Example](/Users/ethan/Repos/captains-log/.claude/agents/code-simplifier.md) - Reference for agent file format
- [Claude Code Subagents Documentation](https://code.claude.com/docs/en/sub-agents) - Official subagent documentation
- [Claude Code Slash Commands](https://code.claude.com/docs/en/slash-commands) - Custom command documentation

## Appendix A: Port Offset Examples

| Offset | Backend (8000) | Frontend (3000) | DB (5432) |
|--------|----------------|-----------------|-----------|
| 0 | 08000 | 03000 | 05432 |
| 1 | 18000 | 13000 | 15432 |
| 2 | 28000 | 23000 | 25432 |
| 3 | 38000 | 38000 | 35432 |
| 4 | 48000 | 43000 | 45432 |
| 5 | 58000 | 53000 | 55432 |

## Appendix B: Knowledge Base Agent File

The single `kb-expert` agent is shown in the Approach section above. This agent:
- Handles all knowledge base documents dynamically
- Receives the document name via the Task tool's prompt parameter
- Uses haiku model for fast, cost-effective responses
- Has Read and Glob tools for document access
