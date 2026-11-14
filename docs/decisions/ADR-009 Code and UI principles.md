---
type: decision
status: accepted
date: 2026-11-15
---
# ADR-009 Code and UI principles

**Status:** accepted

## Decision
Modern, single-theme UI and minimal, human-written code, kept lean by two mid-build checkpoints and one final review-and-removal pass.

## Context
The project is built with many LLM coding agents in parallel, which tend to produce too much code. The owner wants
code that reads like a careful human wrote it.

## Details
**UI**
- Modern look with shadcn/ui defaults: clean spacing, clear typography, cards, tables, charts.
- One light theme. No theme switcher, no dark mode, no custom design system, no animation library.

**Code**
- Minimal code in frontend and backend; clear names; short functions; obvious control flow.
- No function, method, component or file unless something uses it now.
- No duplicated logic; no speculative options, wrappers, base classes, factories or utils grab-bags.

**Review and removal (speed first)**
- No review or code cut on every merge; merges run only the task's acceptance check.
- Checkpoint 1, after the skeleton wave: browser smoke test + review of shared patterns so later agents copy lean code.
- Checkpoint 2, after core services use the real models and RAG: browser check of order and incident flows + targeted cleanup.
- Final pass after all features merge: full review and removal, then full browser verification; report lines removed vs added.
- Reviewer: Opus 5.5 or Fable 5.2; edits by Sonnet 5.5. Maximise parallel sub-agents; never block merges on review.

## Related
- [[Tech Stack]]
- [[ADR-001 Simple stack]]
- [[ADR-002 React with Vite]]
