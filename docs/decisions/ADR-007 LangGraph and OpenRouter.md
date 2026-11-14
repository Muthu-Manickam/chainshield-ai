---
type: decision
status: accepted
date: 2026-11-15
---
# ADR-007 LangGraph and OpenRouter

**Status:** accepted

## Decision
Agents use LangGraph 1.2; LLM calls go to OpenRouter through langchain-openai.

## Context
Both are named in the proposal; OpenRouter lets us switch models without code changes.

## Details
Primary `anthropic/claude-haiku-5.5`, fallback `openai/gpt-5-mini`, then a fixed template. Temperature 0, structured output, cached responses for offline demo.

## Alternatives rejected
Pydantic AI plain pipeline; direct vendor SDKs; LiteLLM (2026 supply-chain incidents).

## Related
- [[Tech Stack]]
- [[ADR-003 Single Python backend]]
