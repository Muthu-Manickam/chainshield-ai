---
type: decision
status: accepted
date: 2026-11-15
---
# ADR-010 Langfuse tracing

**Status:** accepted

## Decision
Trace every agent run and LLM call with Langfuse (cloud, free Hobby tier).

## Context
The owner wants to monitor how agents and the LLM behave. The app already stores investigation steps for its own
UI, but token use, cost, latency and prompt-level traces are easier to inspect in Langfuse.

## Details
- Python SDK `langfuse` 5.2.0, attached through its LangChain callback to both LangGraph graphs.
- Enabled only when `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set; the app works without them.
- Hobby tier: 50k units/month, 30 days of history, 2 users. No self-hosting (needs Postgres, ClickHouse, Redis, S3).
- `investigation_steps` stays the source of truth for the Investigations page and the offline demo.

## Alternatives rejected
LangSmith (SaaS, LangChain-only); self-hosted Langfuse (too many services); own tracing only (no cost/latency views).

## Related
- [[Tech Stack]]
- [[ADR-007 LangGraph and OpenRouter]]
