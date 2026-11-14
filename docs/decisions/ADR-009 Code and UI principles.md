---
type: decision
status: accepted
date: 2026-11-15
---
# ADR-009 Code and UI principles

**Status:** accepted

## Decision
Modern, single-theme UI and minimal, human-written code, enforced by a review-and-removal step before every merge.

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

**Review and removal**
- Before each merge into `release/v1`: review the diff and delete unused code, duplication and needless layers.
- After each wave of merges: cleanup pass over the whole tree; report lines removed vs added.
- Reviewer: Opus 5.5 or Fable 5.2; edits by Sonnet 5.5. Checks and browser flows must still pass afterwards.

## Related
- [[Tech Stack]]
- [[ADR-001 Simple stack]]
- [[ADR-002 React with Vite]]
