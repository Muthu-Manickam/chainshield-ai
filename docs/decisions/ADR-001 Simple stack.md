---
type: decision
status: accepted
date: 2026-11-15
---
# ADR-001 Simple stack

**Status:** accepted

## Decision
Use a deliberately small stack: React + TypeScript (Vite), FastAPI, Postgres + pgvector.

## Context
One developer, built mostly with LLM agents, needs a real frontend, backend and database without extra tooling.

## Details
Locked in `STACK.lock.md`. Add a library only when the code would be clearly longer or worse without it.

## Alternatives rejected
Next.js + Turborepo + pnpm monorepo (too much tooling); Streamlit + SQLite (no real users/dashboards).

## Related
- [[ADR-002 React with Vite]]
- [[ADR-003 Single Python backend]]
- [[ADR-004 Postgres with pgvector]]
