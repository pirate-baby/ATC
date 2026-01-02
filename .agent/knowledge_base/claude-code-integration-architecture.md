# Claude Agent SDK Integration Architecture

## ⚠️ CRITICAL: Claude Code CLI Only - NO Direct API Calls

**This codebase uses the Claude Agent SDK with local Claude Code CLI exclusively.**

### Correct Architecture Flow

```
User Subscription Token → Claude Agent SDK → Claude Code CLI → Anthropic API (internal)
                                                                        ↑
                                                        We NEVER touch this directly
```

### Absolutely Prohibited

❌ **DO NOT** make direct HTTP calls to `api.anthropic.com`
❌ **DO NOT** use `httpx` or `requests` to call `/v1/messages` endpoints
❌ **DO NOT** bypass the Claude Code CLI in any way
❌ **DO NOT** use API headers like `x-api-key` or `anthropic-version`

### Token Source and Types

**CRITICAL: You MUST use Claude Code subscription tokens, NOT Anthropic API keys.**

| Token Type | Prefix | Source | Usage |
|------------|--------|--------|-------|
| ✅ **Subscription Token** | `sk-ant-sid...` | `claude setup-token` command | **CORRECT - Use this** |
| ❌ **API Key** | `sk-ant-api...` | console.anthropic.com | **WRONG - Do NOT use** |

**How to get the correct token:**
1. Install Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
2. Run: `claude setup-token`
3. Follow the authentication flow
4. Copy the generated token (starts with `sk-ant-sid`)

**Why subscription tokens are required:**
- Subscription tokens authenticate against your Claude Pro/Max subscription
- API keys are for direct API usage (bypasses Claude Code CLI)
- The Claude Code CLI only accepts subscription tokens
- API keys will fail or produce unexpected behavior

All tokens in the pool rotation system are **Claude Code subscription tokens** supplied by users. The Claude Code CLI handles all communication with the Anthropic API internally using these subscription tokens. Our code only interacts with the local CLI via the Claude Agent SDK.

**Token Pool Rotation System:**
- ❌ NO environment variables for tokens - all managed in database
- ✅ Users add tokens via `/claude-tokens` API endpoint in UI (Settings → Claude Token)
- ✅ System automatically rotates through available tokens for fair distribution
- ✅ Token usage tracked per token for monitoring and fairness
- ✅ Failed/rate-limited tokens automatically marked and skipped in rotation
- ✅ Backend workers pull tokens from pool when generating plans/tasks

---

## Executive Summary

This document outlines architectural patterns for integrating Claude Code as an execution runtime for planning and coding tasks using the official Claude Agent SDK (Python).

## The Claude Agent SDK

The Claude Code SDK has been renamed to the **Claude Agent SDK** to reflect its broader applicability. The SDK provides the same tools, agent loop, and context management that power Claude Code, programmable in Python and TypeScript.

**Installation**: `pip install claude-agent-sdk`

**Prerequisite**: Claude Code CLI must be installed (`npm install -g @anthropic-ai/claude-code`)

### Key Capabilities

| Capability | Description |
|------------|-------------|
| Built-in Tools | Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch, NotebookEdit, TodoWrite |
| Hooks | Run custom code at key points in the agent lifecycle |
| Subagents | Spawn specialized agents for focused subtasks |
| MCP Integration | Connect to external systems via Model Context Protocol |
| Session Management | Maintain context across multiple exchanges |
| Permission Control | Fine-grained tool authorization |

## Core SDK Components

### Query Function vs ClaudeSDKClient

| Feature | `query()` | `ClaudeSDKClient` |
|---------|-----------|-------------------|
| Session | Creates new session each time | Reuses same session |
| Conversation | Single exchange | Multiple exchanges in same context |
| Connection | Managed automatically | Manual control |
| Interrupts | Not supported | Supported |
| Hooks | Not supported | Supported |
| Custom Tools | Not supported | Supported |
| Use Case | One-off tasks | Continuous conversations |

### When to Use `query()`

- One-off questions without conversation history
- Independent tasks without context from previous exchanges
- Simple automation scripts
- Fresh start each time

### When to Use `ClaudeSDKClient`

- Continuing conversations with context
- Follow-up questions building on previous responses
- Interactive applications and chat interfaces
- Response-driven logic where next action depends on Claude's response
- Session lifecycle control

## Message Types

| Type | Description | Key Fields |
|------|-------------|------------|
| `UserMessage` | User input | `content` |
| `AssistantMessage` | Claude's responses | `content` (list of ContentBlocks), `model` |
| `SystemMessage` | System metadata | `subtype`, `data` |
| `ResultMessage` | Final result | `duration_ms`, `session_id`, `total_cost_usd`, `usage`, `result` |

### Content Block Types

| Type | Purpose |
|------|---------|
| `TextBlock` | Text content from Claude |
| `ThinkingBlock` | Extended thinking (for capable models) |
| `ToolUseBlock` | Tool invocation request |
| `ToolResultBlock` | Tool execution result |

## Session Management Architecture

### Session Lifecycle

1. **Creation**: New query automatically creates a session
2. **Identification**: Session ID returned in initial system message (`subtype == 'init'`)
3. **Resumption**: Pass session ID via `resume` option to continue with full context
4. **Forking**: Use `fork_session=True` to create new branch from existing session state

### Session Patterns

| Pattern | Use Case | Implementation |
|---------|----------|----------------|
| Ephemeral | One-off tasks | New session per request, destroyed on completion |
| Long-Running | Proactive agents | Persistent session with multiple Claude processes |
| Hybrid | Intermittent work | Ephemeral containers hydrated with session history |
| Single Container | Agent collaboration | Multiple SDK processes in shared environment |

## Permission and Security Architecture

### Permission Flow

```
Tool Request → PreToolUse Hook → Deny Rules → Allow Rules → Ask Rules → Permission Mode → canUseTool Callback → Execute → PostToolUse Hook
```

### Permission Modes

| Mode | Behavior |
|------|----------|
| `default` | Standard permission checks apply |
| `acceptEdits` | Auto-approve file edits and filesystem operations |
| `bypassPermissions` | All tools run without prompts (use with caution) |

### canUseTool Callback

The `canUseTool` callback enables custom authorization logic. It receives tool name and input parameters, returning a decision:

**Return Structure:**
```
{
    "behavior": "allow" | "deny",
    "updatedInput": dict,  # Optional: modified input parameters
    "message": str         # Optional: denial reason
}
```

**Use Cases:**
- Dynamic approval based on tool name and parameters
- Path-based restrictions (block writes to system directories)
- Input modification (redirect to sandbox paths)
- User confirmation workflows
- Audit logging

## Hosting and Deployment Architecture

### Container-Based Deployment

The SDK should run inside sandboxed containers providing:
- Process isolation
- Resource limits (recommended: 1GiB RAM, 5GiB disk, 1 CPU)
- Network control (Claude Code CLI handles all external communication internally)
- Ephemeral filesystems

### Sandbox Providers

- Cloudflare Sandboxes
- Modal Sandboxes
- Daytona
- E2B
- Fly Machines
- Vercel Sandbox

### Sandbox Configuration

| Setting | Description |
|---------|-------------|
| `enabled` | Enable command sandboxing |
| `autoAllowBashIfSandboxed` | Auto-approve bash when sandboxed |
| `excludedCommands` | Commands that bypass sandbox (e.g., `["docker"]`) |
| `allowUnsandboxedCommands` | Allow model to request unsandboxed execution |
| `network.allowLocalBinding` | Allow processes to bind to local ports |
| `network.allowUnixSockets` | Unix socket paths that processes can access |

## Multi-Agent Orchestration

### Subagent Architecture

The SDK supports hierarchical agent structures:

1. **Main Orchestrator**: Analyzes requests and routes to specialists
2. **Specialized Agents**: Domain-specific with isolated context
3. **Result Aggregation**: Parent synthesizes outputs before returning

### Agent Definition

| Field | Required | Description |
|-------|----------|-------------|
| `description` | Yes | When to use this agent |
| `prompt` | Yes | Agent's system prompt |
| `tools` | No | Allowed tool names (inherits if omitted) |
| `model` | No | Model override: `sonnet`, `opus`, `haiku`, `inherit` |

### Context Isolation

Each subagent maintains separate context heaps preventing cross-contamination:
- Frontend agent doesn't see backend context
- Database agent isolated from UI concerns
- Tool access restricted per agent

Subagents are invoked via the `Task` tool. Include `Task` in `allowed_tools` to enable subagent spawning.

## Hook System

### Available Hook Events

| Event | Description |
|-------|-------------|
| `PreToolUse` | Before tool execution |
| `PostToolUse` | After tool execution |
| `UserPromptSubmit` | When user submits a prompt |
| `Stop` | When stopping execution |
| `SubagentStop` | When a subagent stops |
| `PreCompact` | Before message compaction |

### Hook Callback Signature

```
async def hook_callback(
    input_data: dict,
    tool_use_id: str | None,
    context: HookContext
) -> dict
```

### Hook Return Options

| Key | Purpose |
|-----|---------|
| `decision` | `"block"` to block the action |
| `systemMessage` | System message to add to transcript |
| `hookSpecificOutput` | Hook-specific output data |

### HookMatcher Configuration

| Field | Description |
|-------|-------------|
| `matcher` | Tool name or regex pattern (e.g., `"Bash"`, `"Write\|Edit"`) |
| `hooks` | List of callback functions |
| `timeout` | Timeout in seconds (default: 60) |

## Tool Extension via MCP

### MCP Server Types

| Type | Description |
|------|-------------|
| `stdio` | Local process communication |
| `sse` | Server-Sent Events over HTTP |
| `http` | HTTP-based transport |
| `sdk` | In-process SDK server |

### Custom Tool Definition

Tools are defined using the `@tool` decorator:

**Decorator Parameters:**
- `name`: Unique identifier for the tool
- `description`: Human-readable description
- `input_schema`: Schema defining input parameters (type mapping or JSON Schema)

**Tool Handler:**
- Async function receiving `args: dict`
- Returns dict with `content` list containing response blocks
- Optional `is_error` flag for error responses

### SDK MCP Server

Use `create_sdk_mcp_server()` to create in-process MCP servers:

| Parameter | Description |
|-----------|-------------|
| `name` | Unique identifier for the server |
| `version` | Server version string (default: "1.0.0") |
| `tools` | List of `@tool` decorated functions |

Tools are accessed as `mcp__<server_name>__<tool_name>` in `allowed_tools`.

## Configuration Architecture

### Workspace/Working Directory Configuration

The Claude Agent SDK provides the `cwd` parameter to specify the working directory where the agent operates:

**Type**: `str | Path | None`
**Default**: `None` (uses current working directory of the calling process)

#### Basic Usage

```python
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions

# Using string path
options = ClaudeAgentOptions(
    cwd="/path/to/project"
)

# Using Path object
options = ClaudeAgentOptions(
    cwd=Path("/path/to/project")
)

async for message in query(
    prompt="Analyze this codebase",
    options=options
):
    print(message)
```

#### How It Works

- All file operations (Read, Write, Edit, Glob, Grep) are executed relative to `cwd`
- Bash commands run with `cwd` as the current working directory
- When `cwd` is `None`, the agent operates in the calling process's current directory
- The agent cannot access files outside `cwd` unless additional directories are specified via `add_dirs`

#### Integration with Worktree Management

In this codebase, we use git worktrees to isolate task execution:

```python
from app.services.git import GitService
from uuid import UUID

# Create worktree for a task
git_service = GitService(worktrees_base_path=Path("/var/lib/atc/worktrees"))
result = git_service.create_task_worktree(
    project_id=UUID("..."),
    task_id=UUID("..."),
    task_title="Implement feature",
    git_url="https://github.com/org/repo.git",
    base_branch="main"
)

# Configure Claude to work in the task's worktree
options = ClaudeAgentOptions(
    cwd=result.worktree_path,  # e.g., "/var/lib/atc/worktrees/tasks/{project_id}/{task_id}"
    allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
    permission_mode="acceptEdits"
)

async for message in query(
    prompt="Implement the feature as described",
    options=options
):
    print(message)
```

#### Additional Directories

To grant access to directories outside the main `cwd`:

```python
options = ClaudeAgentOptions(
    cwd="/path/to/project",
    add_dirs=[
        "/path/to/shared/libraries",
        "/path/to/config"
    ]
)
```

#### Environment Variables

The `env` parameter allows passing environment variables to the agent:

```python
options = ClaudeAgentOptions(
    cwd="/path/to/project",
    env={
        "ANTHROPIC_API_KEY": subscription_token,
        "NODE_ENV": "production",
        "DATABASE_URL": "postgresql://..."
    }
)
```

**Important**: For Claude Code authentication, use `ANTHROPIC_API_KEY` in the `env` dict:

```python
# For subscription tokens (from claude setup-token)
options = ClaudeAgentOptions(
    env={"ANTHROPIC_API_KEY": subscription_token}
)

# Alternative for OAuth tokens (used in debug console)
options = ClaudeAgentOptions(
    env={"CLAUDE_CODE_OAUTH_TOKEN": oauth_token}
)
```

#### Workspace Configuration Pattern for Worker Tasks

When running agents in background workers (like ARQ workers), use this pattern:

```python
async def run_task_execution(
    ctx: dict[str, Any],
    task_id: str,
    subscription_token: str,
) -> dict[str, Any]:
    """Execute a task using Claude Agent SDK in isolated worktree."""
    from app.services.git import GitService
    from claude_agent_sdk import query, ClaudeAgentOptions

    # Get task details from database
    task = get_task(task_id)

    # Create or get worktree for this task
    git_service = GitService(worktrees_base_path=Path("/var/lib/atc/worktrees"))
    result = git_service.create_task_worktree(
        project_id=task.project_id,
        task_id=task.id,
        task_title=task.title,
        git_url=task.project.git_url,
        base_branch=task.project.default_branch
    )

    # Configure agent to work in the task's worktree
    options = ClaudeAgentOptions(
        cwd=result.worktree_path,  # Isolated workspace
        env={"ANTHROPIC_API_KEY": subscription_token},
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        permission_mode="acceptEdits",
        max_turns=50
    )

    # Run the agent
    async for message in query(
        prompt=task.description,
        options=options
    ):
        # Process messages...
        pass

    return {"success": True, "worktree_path": result.worktree_path}
```

### ClaudeAgentOptions

Complete reference for all configuration parameters accepted by `ClaudeAgentOptions`:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `allowed_tools` | `list[str]` | `[]` | List of allowed tool names |
| `disallowed_tools` | `list[str]` | `[]` | List of disallowed tool names |
| `system_prompt` | `str \| SystemPromptPreset \| None` | `None` | System prompt configuration |
| `permission_mode` | `PermissionMode \| None` | `None` | Permission mode for tool usage |
| `mcp_servers` | `dict[str, McpServerConfig] \| str \| Path` | `{}` | MCP server configurations or path to config file |
| `resume` | `str \| None` | `None` | Session ID to resume |
| `fork_session` | `bool` | `False` | Fork session when resuming |
| `continue_conversation` | `bool` | `False` | Continue the most recent conversation |
| `max_turns` | `int \| None` | `None` | Maximum conversation turns |
| `model` | `str \| None` | `None` | Claude model to use |
| `output_format` | `OutputFormat \| None` | `None` | Define output format for agent results |
| `permission_prompt_tool_name` | `str \| None` | `None` | MCP tool name for permission prompts |
| **`cwd`** | **`str \| Path \| None`** | **`None`** | **Current working directory** |
| `settings` | `str \| None` | `None` | Path to settings file |
| `add_dirs` | `list[str \| Path]` | `[]` | Additional directories Claude can access |
| **`env`** | **`dict[str, str]`** | **`{}`** | **Environment variables** |
| `extra_args` | `dict[str, str \| None]` | `{}` | Additional CLI arguments |
| `max_buffer_size` | `int \| None` | `None` | Maximum bytes when buffering CLI stdout |
| `stderr` | `Callable[[str], None] \| None` | `None` | Callback function for stderr output |
| `can_use_tool` | `CanUseTool \| None` | `None` | Tool permission callback function |
| `hooks` | `dict[HookEvent, list[HookMatcher]] \| None` | `None` | Hook configurations |
| `user` | `str \| None` | `None` | User identifier |
| `include_partial_messages` | `bool` | `False` | Include partial message streaming events |
| `agents` | `dict[str, AgentDefinition] \| None` | `None` | Programmatically defined subagents |
| `plugins` | `list[SdkPluginConfig]` | `[]` | Load custom plugins from local paths |
| `setting_sources` | `list[SettingSource] \| None` | `None` | Which filesystem settings to load (None = no settings) |
| `sandbox` | `SandboxSettings \| None` | `None` | Sandbox behavior configuration |
| `enable_file_checkpointing` | `bool` | `False` | Enable file change tracking for rewinding |

### Setting Sources

| Value | Location | Description |
|-------|----------|-------------|
| `"user"` | `~/.claude/settings.json` | Global user settings |
| `"project"` | `.claude/settings.json` | Shared project settings |
| `"local"` | `.claude/settings.local.json` | Local project settings (gitignored) |

**Default behavior**: When `setting_sources` is omitted, no filesystem settings are loaded.

### Filesystem-Based Features

| Feature | Location | Purpose |
|---------|----------|---------|
| Skills | `.claude/skills/SKILL.md` | Specialized capabilities |
| Slash Commands | `.claude/commands/*.md` | Custom commands |
| Memory | `CLAUDE.md` | Project context and instructions |

Requires `setting_sources=["project"]` to load these features.

## Error Handling

| Error Type | Cause | Handling |
|------------|-------|----------|
| `CLINotFoundError` | Claude Code CLI not installed | Install CLI, restart terminal |
| `CLIConnectionError` | Connection to Claude Code failed | Check network, restart CLI |
| `ProcessError` | Claude Code process failed | Check `exit_code` and `stderr` |
| `CLIJSONDecodeError` | JSON parsing failed | Check `line` and `original_error` |

## Integration Architecture

### Key Integration Points

1. **Task Queue Integration**: Feed prompts from task management system
2. **Session Store**: Persist session IDs for resume/fork capabilities
3. **Output Streaming**: Process `async for` messages for real-time UI updates
4. **Cost Tracking**: Capture `ResultMessage.total_cost_usd` and `usage` for billing
5. **Audit Logging**: Implement hooks to track all tool usage

### Recommended Architecture

1. **Use `ClaudeSDKClient`** for multi-turn conversations requiring context
2. **Use `query()`** for one-off tasks without session continuity
3. **Implement hooks** for audit logging, security validation, and behavior modification
4. **Define custom tools** via MCP for domain-specific capabilities
5. **Configure sandbox settings** for production deployment
6. **Implement `canUseTool`** callback for custom authorization logic
7. **Set `setting_sources`** explicitly to control which configurations load

## References

### Official Documentation

- [Claude Agent SDK Overview](https://platform.claude.com/docs/en/api/agent-sdk/overview)
- [Python SDK Reference](https://platform.claude.com/docs/en/agent-sdk/python)
- [Session Management](https://platform.claude.com/docs/en/agent-sdk/sessions)
- [Permissions Guide](https://platform.claude.com/docs/en/agent-sdk/permissions)
- [Hosting Guide](https://platform.claude.com/docs/en/agent-sdk/hosting)
- [Hooks Guide](https://platform.claude.com/docs/en/agent-sdk/hooks)
- [MCP Integration](https://platform.claude.com/docs/en/agent-sdk/mcp)

### Example Implementations

- [Claude Agent SDK Demos](https://github.com/anthropics/claude-agent-sdk-demos)
- [Python SDK GitHub](https://github.com/anthropics/claude-agent-sdk-python)
