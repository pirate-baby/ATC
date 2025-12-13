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

**Implementation Options Evaluated:**

1. **Static Agent Files** (Recommended): Create `.claude/agents/<doc-name>.md` files
   - Each file contains frontmatter (name, description, model) and system prompt
   - System prompt instructs agent to be expert on specific document
   - Agent reads document content at invocation time
   - Pros: Simple, works with existing Claude infrastructure
   - Cons: Requires one file per knowledge document

2. **Dynamic CLI Invocation**: Use `--agents` flag with JSON
   - Could theoretically generate agent definitions at runtime
   - Pros: Flexible, single configuration point
   - Cons: Complex to implement, may not integrate with file-based workflow

3. **Custom Slash Commands**: Use `.claude/commands/` directory
   - Not suitable: commands are prompts, not agents with separate context
   - Would pollute primary context

**Recommended Approach - Static Agent Files:**

Create `.claude/agents/knowledge_base/` directory with agent files:
```
.claude/agents/knowledge_base/
├── architecture.md      # Expert on architecture.md
├── api-design.md        # Expert on api-design.md
└── ...                   # One per knowledge doc
```

Each agent file structure:
```markdown
---
name: kb-<document-slug>
description: Expert on <document-name> - invoke when questions relate to <topic>
model: inherit
---

You are an expert on the document `.agents/knowledge_base/<document-name>.md`.

When invoked:
1. Read the document using the Read tool
2. Answer questions based solely on document content
3. Provide succinct, accurate responses
4. Quote relevant sections when helpful
5. Acknowledge if information is not in the document
```

**Tradeoff Decision**: While a dynamic approach would be more elegant (single config generating agents for all docs), the static approach:
- Works immediately with Claude's existing agent system
- Provides explicit control over each agent's behavior
- Allows customization per document type
- Integrates with version control naturally

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Port conflicts between worktrees | High | Port offset algorithm with validation |
| Knowledge agents become stale | Medium | Agents read documents at runtime, not cached |
| Docker resource leaks | Medium | Dual-filter cleanup (labels + name patterns) |
| Port offset exhaustion (6+ worktrees) | Low | Clear error messaging; unlikely use case |
| Agent files out of sync with knowledge_base | Medium | Documentation; could add validation script |

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
   - Create `.agents/knowledge_base/` directory
   - Create initial knowledge documents
   - Document the knowledge base system

5. **Task: Create Knowledge Base Agent Template**
   - Design agent file template
   - Create generator script (optional) for new docs
   - Document agent creation process

6. **Task: Create Dev Convenience Script**
   - Combine startup + docker compose up
   - Open browser to correct port
   - Display status information

## References

- [Captain's Log - utils/start.sh](/Users/ethan/Repos/captains-log/utils/start.sh) - Reference implementation for port offset and project naming
- [Captain's Log - docker-compose.yml](/Users/ethan/Repos/captains-log/docker-compose.yml) - Reference for port variable substitution
- [Claude Code Agent Example](/Users/ethan/Repos/captains-log/.claude/agents/code-simplifier.md) - Reference for agent file format
- [Claude CLI --agents flag](claude --help) - JSON agent definition format

## Appendix A: Port Offset Examples

| Offset | Backend (8000) | Frontend (3000) | DB (5432) |
|--------|----------------|-----------------|-----------|
| 0 | 08000 | 03000 | 05432 |
| 1 | 18000 | 13000 | 15432 |
| 2 | 28000 | 23000 | 25432 |
| 3 | 38000 | 38000 | 35432 |
| 4 | 48000 | 43000 | 45432 |
| 5 | 58000 | 53000 | 55432 |

## Appendix B: Agent File Template

```markdown
---
name: kb-<slug>
description: Knowledge expert on <Document Title>. Invoke when questions relate to <topics covered>.
model: inherit
color: blue
---

You are an expert on the ATC knowledge base document: `.agents/knowledge_base/<filename>.md`

## Your Expertise

You have deep knowledge of <document subject>. You can answer questions about:
- <topic 1>
- <topic 2>
- <topic 3>

## Instructions

1. **First**: Read the knowledge document using the Read tool
2. **Answer**: Based solely on the document content
3. **Be Succinct**: Provide concise, direct answers
4. **Quote**: Reference specific sections when helpful
5. **Acknowledge Limits**: If information is not in the document, say so

## Response Format

- Lead with the direct answer
- Support with relevant quotes or references
- Keep responses focused and brief
- Use bullet points for multiple items
```
