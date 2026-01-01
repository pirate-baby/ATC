"""Claude Agent SDK integration for AI-powered plan generation.

Uses the Claude Agent SDK to generate plan content based on project context.

IMPORTANT: This module uses the Claude Agent SDK with the local Claude Code CLI only.
It does NOT make direct HTTP calls to the Anthropic API. All communication goes through
the Claude Code CLI which handles API interactions internally using user subscription tokens.
"""

import json
import logging
from dataclasses import dataclass, field
from uuid import UUID

from app.config import settings

logger = logging.getLogger(__name__)


class ClaudeServiceError(Exception):
    """Base exception for Claude service errors."""

    pass


class ClaudeNotConfiguredError(ClaudeServiceError):
    """Raised when Anthropic API key is not configured."""

    pass


class ClaudeGenerationError(ClaudeServiceError):
    """Raised when plan generation fails."""

    pass


@dataclass
class GenerationResult:
    """Result of a plan generation request."""

    content: str
    total_cost_usd: float | None = None
    duration_ms: int | None = None


@dataclass
class GeneratedTask:
    """A task generated from a plan."""

    title: str
    description: str
    blocked_by_indices: list[int] = field(default_factory=list)


@dataclass
class TaskGenerationResult:
    """Result of task generation from a plan."""

    tasks: list[GeneratedTask]
    total_cost_usd: float | None = None
    duration_ms: int | None = None


# Default prompt template for plan generation
PLAN_GENERATION_PROMPT = """You are a software architect helping to create a detailed implementation plan.

Given the following plan title and any additional context, generate a comprehensive markdown document that includes:

1. **Overview**: A brief summary of what this plan aims to accomplish
2. **Goals**: Clear, measurable objectives
3. **Technical Approach**: High-level architecture and design decisions
4. **Implementation Steps**: Numbered list of concrete tasks to complete
5. **Dependencies**: Any external dependencies or prerequisites
6. **Risks & Mitigations**: Potential challenges and how to address them
7. **Success Criteria**: How we'll know the plan is complete

Keep the plan practical, actionable, and appropriate for a development team to execute.

---

**Plan Title**: {title}

{context_section}

Generate the plan content in markdown format:"""


async def generate_plan_content(
    plan_id: UUID,
    title: str,
    context: str | None = None,
    project_context: str | None = None,
) -> GenerationResult:
    """Generate plan content using the Claude Agent SDK.

    Args:
        plan_id: UUID of the plan being generated
        title: Title of the plan
        context: Additional context provided by the user
        project_context: Context about the project (e.g., repository info)

    Returns:
        GenerationResult with the generated content

    Raises:
        ClaudeNotConfiguredError: If Anthropic API key is not set
        ClaudeGenerationError: If generation fails
    """
    if not settings.anthropic_api_key:
        raise ClaudeNotConfiguredError(
            "Claude Code subscription token not configured. Users should add tokens via /claude-tokens API."
        )

    # Build context section
    context_parts = []
    if project_context:
        context_parts.append(f"**Project Context**:\n{project_context}")
    if context:
        context_parts.append(f"**Additional Context**:\n{context}")

    context_section = "\n\n".join(context_parts) if context_parts else ""

    prompt = PLAN_GENERATION_PROMPT.format(
        title=title,
        context_section=context_section,
    )

    try:
        # Import here to avoid import errors if SDK not installed
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            TextBlock,
            query,
        )

        logger.info(f"Starting plan generation for plan_id={plan_id}, title='{title}'")
        logger.debug(f"Prompt length: {len(prompt)} characters")

        # Configure options for plan generation
        # Pass subscription token to Claude Code CLI via environment variable
        # The CLI handles all API communication internally
        options = ClaudeAgentOptions(
            max_turns=1,  # Single turn for plan generation
            env={"ANTHROPIC_API_KEY": settings.anthropic_api_key},
        )

        # Use query() async iterator to collect responses
        content_parts: list[str] = []
        message_count = 0
        async for message in query(prompt=prompt, options=options):
            message_count += 1
            logger.debug(f"Received message #{message_count} from Claude SDK")
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        content_parts.append(block.text)
                        logger.debug(f"Added text block with {len(block.text)} characters")

        generated_content = "\n".join(content_parts)

        if not generated_content:
            logger.error(f"No content generated from Claude for plan_id={plan_id}")
            raise ClaudeGenerationError("No content generated from Claude")

        logger.info(
            f"Plan generation completed for plan_id={plan_id}, "
            f"content_length={len(generated_content)}, messages={message_count}"
        )

        return GenerationResult(
            content=generated_content,
            total_cost_usd=None,
            duration_ms=None,
        )

    except ImportError as e:
        logger.error(f"Claude Agent SDK not installed: {e!r}", exc_info=True)
        raise ClaudeNotConfiguredError(
            "Claude Agent SDK not installed. Run: pip install claude-agent-sdk"
        ) from e
    except Exception as e:
        logger.error(
            f"Plan generation failed for plan_id={plan_id}: {e!r}",
            exc_info=True,
        )
        raise ClaudeGenerationError(f"Failed to generate plan content: {e}") from e


# Prompt template for generating tasks from approved plans
TASK_GENERATION_PROMPT = """You are a software project manager breaking down an approved implementation plan into discrete, actionable tasks.

Given the plan below, decompose it into a list of tasks that can be executed by developers (or coding agents). Each task should:

1. Be atomic and independently implementable
2. Have a clear title (concise, action-oriented)
3. Have a detailed description explaining what needs to be done
4. Specify dependencies on other tasks (by their index in the list)

The tasks should form a DAG (Directed Acyclic Graph) where:
- Tasks with no dependencies can be started immediately
- Tasks with dependencies must wait for those dependencies to complete
- There should be no circular dependencies

Output your response as a JSON object with the following structure:
```json
{{
  "tasks": [
    {{
      "title": "Task title",
      "description": "Detailed description of what needs to be done",
      "blocked_by_indices": []
    }},
    {{
      "title": "Another task",
      "description": "Description...",
      "blocked_by_indices": [0]
    }}
  ]
}}
```

Important:
- blocked_by_indices is a list of 0-based indices referring to other tasks in the list
- The first task has index 0, second has index 1, etc.
- A task can only be blocked by tasks that appear BEFORE it in the list
- Output ONLY the JSON object, no additional text or markdown

---

**Plan Title**: {title}

**Plan Content**:
{content}

{context_section}

Generate the tasks JSON:"""


async def generate_tasks_from_plan(
    plan_id: UUID,
    title: str,
    content: str,
    project_context: str | None = None,
) -> TaskGenerationResult:
    """Generate tasks from an approved plan using Claude.

    Args:
        plan_id: UUID of the plan being decomposed
        title: Title of the plan
        content: The plan content to decompose
        project_context: Context about the project

    Returns:
        TaskGenerationResult with the generated tasks

    Raises:
        ClaudeNotConfiguredError: If Anthropic API key is not set
        ClaudeGenerationError: If generation fails
    """
    if not settings.anthropic_api_key:
        raise ClaudeNotConfiguredError(
            "Claude Code subscription token not configured. Users should add tokens via /claude-tokens API."
        )

    # Build context section
    context_section = ""
    if project_context:
        context_section = f"**Project Context**:\n{project_context}"

    prompt = TASK_GENERATION_PROMPT.format(
        title=title,
        content=content,
        context_section=context_section,
    )

    try:
        # Import here to avoid import errors if SDK not installed
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            TextBlock,
            query,
        )

        logger.info(f"Starting task generation for plan_id={plan_id}, title='{title}'")
        logger.debug(f"Prompt length: {len(prompt)} characters, content length: {len(content)} characters")

        # Configure options for task generation
        # Pass subscription token to Claude Code CLI via environment variable
        # The CLI handles all API communication internally
        options = ClaudeAgentOptions(
            max_turns=1,
            env={"ANTHROPIC_API_KEY": settings.anthropic_api_key},
        )

        # Use query() async iterator to collect responses
        content_parts: list[str] = []
        message_count = 0
        async for message in query(prompt=prompt, options=options):
            message_count += 1
            logger.debug(f"Received message #{message_count} from Claude SDK for task generation")
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        content_parts.append(block.text)
                        logger.debug(f"Added text block with {len(block.text)} characters")

        generated_content = "\n".join(content_parts)

        if not generated_content:
            logger.error(f"No content generated from Claude for task generation, plan_id={plan_id}")
            raise ClaudeGenerationError("No content generated from Claude")

        logger.debug(f"Parsing tasks from {len(generated_content)} characters of response")

        # Parse the JSON response
        tasks = _parse_tasks_from_response(generated_content)

        logger.info(
            f"Task generation completed for plan_id={plan_id}, "
            f"generated {len(tasks)} tasks, messages={message_count}"
        )

        return TaskGenerationResult(
            tasks=tasks,
            total_cost_usd=None,
            duration_ms=None,
        )

    except ImportError as e:
        logger.error(f"Claude Agent SDK not installed: {e!r}", exc_info=True)
        raise ClaudeNotConfiguredError(
            "Claude Agent SDK not installed. Run: pip install claude-agent-sdk"
        ) from e
    except ClaudeGenerationError:
        raise
    except Exception as e:
        logger.error(
            f"Task generation failed for plan_id={plan_id}: {e!r}",
            exc_info=True,
        )
        raise ClaudeGenerationError(f"Failed to generate tasks from plan: {e}") from e


def _parse_tasks_from_response(response: str) -> list[GeneratedTask]:
    """Parse the JSON response from Claude into GeneratedTask objects.

    Args:
        response: The raw response from Claude (should be JSON)

    Returns:
        List of GeneratedTask objects

    Raises:
        ClaudeGenerationError: If parsing fails
    """
    logger.debug(f"Parsing task response with {len(response)} characters")

    # Try to extract JSON from the response (in case there's surrounding text)
    json_str = response.strip()

    # Handle markdown code blocks
    if "```json" in json_str:
        logger.debug("Found JSON markdown code block in response")
        start = json_str.find("```json") + 7
        end = json_str.find("```", start)
        json_str = json_str[start:end].strip()
    elif "```" in json_str:
        logger.debug("Found generic markdown code block in response")
        start = json_str.find("```") + 3
        end = json_str.find("```", start)
        json_str = json_str[start:end].strip()

    try:
        data = json.loads(json_str)
        logger.debug(f"Successfully parsed JSON with keys: {list(data.keys())}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse tasks JSON: {e!r}", exc_info=True)
        logger.debug(f"Failed JSON string (first 500 chars): {json_str[:500]}")
        raise ClaudeGenerationError(f"Failed to parse tasks JSON: {e}") from e

    if not isinstance(data, dict) or "tasks" not in data:
        logger.error(f"Invalid response format: missing 'tasks' key. Keys found: {list(data.keys())}")
        raise ClaudeGenerationError("Invalid response format: missing 'tasks' key")

    tasks_data = data["tasks"]
    if not isinstance(tasks_data, list):
        logger.error(f"Invalid response format: 'tasks' is {type(tasks_data)} instead of list")
        raise ClaudeGenerationError("Invalid response format: 'tasks' must be a list")

    logger.debug(f"Parsing {len(tasks_data)} tasks from response")

    tasks: list[GeneratedTask] = []
    for i, task_data in enumerate(tasks_data):
        if not isinstance(task_data, dict):
            logger.error(f"Invalid task at index {i}: {type(task_data)} instead of dict")
            raise ClaudeGenerationError(f"Invalid task at index {i}: must be an object")

        title = task_data.get("title")
        description = task_data.get("description")

        if not title or not isinstance(title, str):
            logger.error(f"Invalid task at index {i}: missing or invalid title")
            raise ClaudeGenerationError(f"Invalid task at index {i}: missing or invalid 'title'")
        if not description or not isinstance(description, str):
            logger.error(f"Invalid task at index {i}: missing or invalid description")
            raise ClaudeGenerationError(f"Invalid task at index {i}: missing or invalid 'description'")

        blocked_by = task_data.get("blocked_by_indices", [])
        if not isinstance(blocked_by, list):
            logger.warning(f"Task {i} has invalid blocked_by_indices (not a list), using empty list")
            blocked_by = []

        # Validate blocked_by indices
        valid_blocked_by = []
        for idx in blocked_by:
            if isinstance(idx, int) and 0 <= idx < i:
                valid_blocked_by.append(idx)
            else:
                logger.warning(f"Task {i} ('{title}') has invalid blocked_by index {idx}, skipping")

        logger.debug(f"Parsed task {i}: '{title}' with {len(valid_blocked_by)} dependencies")

        tasks.append(GeneratedTask(
            title=title,
            description=description,
            blocked_by_indices=valid_blocked_by,
        ))

    logger.debug(f"Successfully parsed {len(tasks)} tasks")
    return tasks


class ClaudeService:
    """Service class for Claude API operations.

    Provides a structured interface for plan generation and other
    Claude-powered operations.
    """

    def __init__(self):
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate that required configuration is present."""
        if not settings.anthropic_api_key:
            logger.warning(
                "Claude Code subscription token not configured. Claude features will be unavailable."
            )

    @property
    def is_configured(self) -> bool:
        """Check if the Claude service is properly configured."""
        return bool(settings.anthropic_api_key)

    async def generate_plan(
        self,
        plan_id: UUID,
        title: str,
        context: str | None = None,
        project_context: str | None = None,
    ) -> GenerationResult:
        """Generate plan content.

        Args:
            plan_id: UUID of the plan
            title: Plan title
            context: Additional user-provided context
            project_context: Project-specific context

        Returns:
            GenerationResult with generated content

        Raises:
            ClaudeNotConfiguredError: If API key not set
            ClaudeGenerationError: If generation fails
        """
        return await generate_plan_content(
            plan_id=plan_id,
            title=title,
            context=context,
            project_context=project_context,
        )

    async def generate_tasks(
        self,
        plan_id: UUID,
        title: str,
        content: str,
        project_context: str | None = None,
    ) -> TaskGenerationResult:
        """Generate tasks from an approved plan.

        Args:
            plan_id: UUID of the plan
            title: Plan title
            content: Plan content to decompose
            project_context: Project-specific context

        Returns:
            TaskGenerationResult with generated tasks

        Raises:
            ClaudeNotConfiguredError: If API key not set
            ClaudeGenerationError: If generation fails
        """
        return await generate_tasks_from_plan(
            plan_id=plan_id,
            title=title,
            content=content,
            project_context=project_context,
        )


# Global service instance
claude_service = ClaudeService()
