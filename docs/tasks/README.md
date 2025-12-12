# Tasks

This directory contains task specifications that materialize the plans into actionable work items.

## Purpose

Tasks define **how** we execute the plans. They capture:

- Concrete implementation steps
- Acceptance criteria
- Dependencies
- Progress tracking

## Relationship to Plans

```
Plans (what/why) --> Tasks (how/when)
```

Tasks should always reference the plan(s) they implement.

## Task Execution Workflow

When executing a task, follow this test-driven development (TDD) workflow:

1. **Identify test changes** - Determine what new tests need to be written, and which existing tests need to be modified or removed to support the new behavior
2. **Update tests** - Write or modify the tests per step 1
3. **Verify test failures** - Run tests and confirm they fail for the expected reasons
4. **Implement the feature** - Make application changes to pass all tests
5. **Refine the code** - Improve quality, readability, and adherence to best practices
6. **Lint and format** - Run linters and formatters to ensure code consistency
7. **Mark ready for review** - Task is complete and ready for human review

## Naming Convention

```
NNNN-<slug>.md
```

- `NNNN`: Four-digit sequence number (e.g., `0001`)
- `<slug>`: Kebab-case descriptor (e.g., `setup-fastapi`, `create-auth-flow`)

## Task Structure

Each task should include:

1. **Title** - Clear, actionable name
2. **Status** - Todo | In Progress | In Review | Done | Blocked | Cancelled
3. **Plan Reference** - Link to parent plan(s)
4. **Assignee** - Who is responsible (human or AI agent)
5. **Priority** - Critical | High | Medium | Low
6. **Summary** - Brief description of the work
7. **Acceptance Criteria** - Checklist of completion requirements
8. **Implementation Notes** - Technical details, approach
9. **Dependencies** - Other tasks that must complete first
10. **Blockers** - Current impediments (if any)
11. **Log** - Timestamped progress updates

## Index

| # | Task | Status | Priority | Plan |
|---|------|--------|----------|------|
| - | - | - | - | No tasks yet |
