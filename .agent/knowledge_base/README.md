# Knowledge Base

This directory contains knowledge documents for Claude agent context during work sessions.

## Purpose

These documents are **not human documentation**. They are structured reference materials designed for the `kb-expert` subagent to query when the orchestrating Claude needs accurate, contextual information about ATC.

## How It Works

1. The orchestrating Claude identifies a need for project knowledge
2. It invokes the `kb-expert` agent via the Task tool with a specific query
3. The `kb-expert` reads the relevant document(s) from this directory
4. It returns a succinct, accurate answer based on document content

## Document Guidelines

### Writing for Agents

- **Be factual**: State facts, not opinions
- **Be structured**: Use headers, tables, and lists for easy parsing
- **Be complete**: Include all relevant details—agents can't ask follow-up questions
- **Be current**: Update documents when the project changes
- **Avoid prose**: Dense paragraphs are harder to parse than structured content

### File Naming

- Use lowercase with hyphens: `project-overview.md`
- Keep names descriptive but concise
- Avoid special characters and spaces

### Content Structure

Each document should include:

1. **Title**: Clear `# Header` identifying the topic
2. **Context**: Brief explanation of what the document covers
3. **Content**: Structured information using appropriate markdown
4. **Cross-references**: Links to related documents when relevant

## Current Documents

| Document | Purpose |
|----------|---------|
| `project-overview.md` | High-level project description, mission, and status |
| `architecture.md` | System architecture, tech stack, and design decisions |
| `conventions.md` | Coding conventions and patterns used in the codebase |

## Adding New Documents

When adding a new knowledge document:

1. Create the file in this directory with a descriptive name
2. Follow the writing guidelines above
3. Update this README's document table
4. No changes needed to the `kb-expert` agent—it handles all documents dynamically

## Usage Example

The orchestrating Claude might invoke:

```
Task(
  subagent_type: "kb-expert",
  prompt: "Consult architecture.md: What port offset system does ATC use for parallel worktrees?"
)
```

The `kb-expert` would:
1. Read `.agent/knowledge_base/architecture.md`
2. Find the Port Offset System section
3. Return a concise answer about offsets 0-5 and how they're assigned

## Not For

- User-facing documentation (use project README or docs site)
- API documentation (use OpenAPI/Swagger)
- Temporary notes or drafts
- Meeting notes or discussions
