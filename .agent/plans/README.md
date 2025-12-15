# Plans

This directory contains strategic planning documents for the ATC (Automated Team Collaboration) project.

## Purpose

Plans define **what** we want to build and **why**. They capture:

- Vision and goals
- Architecture decisions
- Design principles
- Rules of engagement
- Success criteria

**Important**: Plans describe features, functionality, and architectural patterns in prose. They should **not** include code, pseudo-code, or specific file change instructions. Implementation details belong in tasks.

## Naming Convention

```
NNNN-<slug>.md
```

- `NNNN`: Four-digit sequence number (e.g., `0001`)
- `<slug>`: Kebab-case descriptor (e.g., `project-vision`, `api-design`)

## Plan Structure

Each plan should include:

1. **Title** - Clear, descriptive name
2. **Status** - Draft | Review | Approved | Superseded
3. **Author(s)** - Who wrote this plan
4. **Date** - Creation and last updated dates
5. **Summary** - Brief overview (2-3 sentences)
6. **Context** - Background and motivation
7. **User Roles** - Who will use this feature and their needs
8. **User Stories** - Scenarios describing user interactions
9. **Goals** - What this plan aims to achieve
10. **Non-Goals** - Explicitly out of scope
11. **Acceptance Criteria** - Testable requirements using EARS format (see below)
12. **Approach** - High-level description of the solution (no code)
13. **Risks & Mitigations** - Known risks and how to address them
14. **References** - Links to related plans, tasks, or external resources

## EARS Format for Acceptance Criteria

Use the EARS (Easy Approach to Requirements Syntax) format for testable criteria:

- **Event-driven**: "When [event], the system shall [response]"
- **State-driven**: "While [state], the system shall [behavior]"
- **Conditional**: "If [condition], then the system shall [action]"

This ensures acceptance criteria are unambiguous and directly testable.

## Index

| # | Plan | Status | Description |
|---|------|--------|-------------|
| 0001 | [Basic Repo Structure](0001-basic-repo-structure.md) | Draft | Docker services, worktree namespacing, knowledge base subagents |
