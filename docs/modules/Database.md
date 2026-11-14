---
type: module
status: planned
path: backend/chainshield/db/
---
# Database

**Path:** `backend/chainshield/db/`
**Status:** planned

## Purpose
SQLAlchemy models, Alembic migrations, seed scripts, Postgres + pgvector in Docker.

## Scope
Tables: users, roles, user_roles, orders, order_risk, incidents, incident_classifications, review_queue, documents, chunks, investigations, agent_steps, citations, actions, rule_checks, approvals, rules, model_versions, eval_results, llm_cache, audit_log.

## Related
- [[ADR-004 Postgres with pgvector]]

## Notes
