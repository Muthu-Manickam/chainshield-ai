---
type: decision
status: accepted
date: 2026-11-15
---
# ADR-002 React with Vite

**Status:** accepted

## Decision
Frontend is React 19 + TypeScript 5.9 built with Vite 8, styled with Tailwind 4 and shadcn/ui.

## Context
FastAPI is the backend, so server-side rendering adds a second server for no benefit.

## Details
Libraries: react-router (pages), TanStack Query (API calls), Recharts via shadcn charts, lucide icons. Nothing else.

## Alternatives rejected
Next.js (second server); TanStack Table, react-hook-form, zod, codegen (not needed yet).

## Related
- [[Tech Stack]]
- [[ADR-008 TypeScript 5.9]]
