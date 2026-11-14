---
type: decision
status: accepted
date: 2026-11-15
---
# ADR-004 Postgres with pgvector

**Status:** accepted

## Decision
One database: PostgreSQL 18 with pgvector 0.8.7, run in Docker.

## Context
Relational data (users, orders, investigations) and embeddings in one place; real-world skill; hybrid search in one SQL query.

## Details
Embeddings in `vector(384)` with HNSW index; keyword search via `tsvector`; LLM cache as a table. Raw data and weights stay as files.

## Alternatives rejected
SQLite + NumPy (no users/concurrency story); Chroma/FAISS/Pinecone (second store to sync).

## Related
- [[Tech Stack]]
- [[ADR-003 Single Python backend]]
