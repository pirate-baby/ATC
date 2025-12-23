"""Claude Agent SDK integration for AI-powered plan generation.

Uses the Claude Agent SDK to generate plan content based on project context.
"""

import asyncio
import logging
from dataclasses import dataclass
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
            "Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable."
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
        from claude_agent_sdk import query

        logger.info(f"Starting plan generation for plan_id={plan_id}")

        # Use query() for one-off generation tasks
        # The SDK handles the agent loop internally
        result = await asyncio.to_thread(
            query,
            prompt,
            options={
                "model": "claude-sonnet-4-20250514",
                "max_turns": 1,  # Single turn for plan generation
                "allowed_tools": [],  # No tools needed for content generation
            },
        )

        # Extract the generated content from the result
        # The result contains messages; we need to extract text content
        generated_content = _extract_content_from_result(result)

        if not generated_content:
            raise ClaudeGenerationError("No content generated from Claude")

        logger.info(f"Plan generation completed for plan_id={plan_id}")

        return GenerationResult(
            content=generated_content,
            total_cost_usd=getattr(result, "total_cost_usd", None),
            duration_ms=getattr(result, "duration_ms", None),
        )

    except ImportError as e:
        logger.error(f"Claude Agent SDK not installed: {e}")
        raise ClaudeNotConfiguredError(
            "Claude Agent SDK not installed. Run: pip install claude-agent-sdk"
        ) from e
    except Exception as e:
        logger.error(f"Plan generation failed for plan_id={plan_id}: {e}")
        raise ClaudeGenerationError(f"Failed to generate plan content: {e}") from e


def _extract_content_from_result(result) -> str:
    """Extract text content from Claude SDK result.

    The result object contains messages with content blocks.
    We extract all text blocks and combine them.
    """
    content_parts = []

    # Handle the result based on SDK response structure
    if hasattr(result, "result") and result.result:
        # ResultMessage has a 'result' field with the final content
        return result.result

    if hasattr(result, "messages"):
        for message in result.messages:
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        content_parts.append(block.text)

    return "\n".join(content_parts)


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
                "Anthropic API key not configured. Claude features will be unavailable."
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


# Global service instance
claude_service = ClaudeService()
