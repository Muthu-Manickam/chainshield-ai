---
type: decision
status: accepted
date: 2026-11-15
---
# ADR-003 Single Python backend

**Status:** accepted

## Decision
All business logic, ML inference and agents live in one FastAPI app.

## Context
Models and agents are Python; a TypeScript backend would duplicate types and logic.

## Details
FastAPI 0.163 + Pydantic 2.14 + SQLAlchemy 2.1 (sync) + Alembic. Agent runs use FastAPI BackgroundTasks; live progress via StreamingResponse.

## Alternatives rejected
Node/Express backend; Redis + Celery workers (unneeded at this scale).

## Related
- [[Backend API]]
- [[Agents]]
