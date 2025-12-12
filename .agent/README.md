# ATC Agent Guidance

**Automated Team Collaboration** - Redefining SDLC for the AI-enabled age.

> ATC: Where software takes flight under human guidance.

## Purpose

This directory contains agent guidance for bootstrapping ATC development. It defines **what** to build (plans) and **how** to build it (tasks) until ATC can manage itself.

## Structure

```
.agent/
├── README.md          # This file
├── plans/             # Strategic planning documents (what/why)
│   └── README.md      # Plan guidelines and index
└── tasks/             # Execution specifications (how)
    └── README.md      # Task guidelines and index
```

## Workflow

1. **Plan** - Define features, architecture, and rules in `plans/`
2. **Task** - Break plans into actionable work items in `tasks/`
3. **Execute** - Implement tasks using TDD with full traceability to plans

## Tech Stack

- **Backend**: Python (FastAPI)
- **Frontend**: React
- **Theme**: Air Traffic Control interface

## Getting Started

Start by reading the plans in order. The first plan should establish the project vision and rules of engagement.
