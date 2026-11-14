---
type: decision
status: accepted
date: 2026-11-15
---
# ADR-008 TypeScript 5.9

**Status:** accepted

## Decision
Pin TypeScript 5.9.3, not 7.x.

## Context
Some tooling (e.g. openapi-typescript) only supports TypeScript 5; 7.0 is a fresh rewrite.

## Details
Pinned in `frontend/package.json`.

## Alternatives rejected
TypeScript 7.0.2.

## Related
- [[Tech Stack]]
- [[ADR-002 React with Vite]]
