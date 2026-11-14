---
type: module
status: planned
path: backend/chainshield/rag/
---
# RAG

**Path:** `backend/chainshield/rag/`
**Status:** planned

## Purpose
Ingest guidance documents, chunk, embed, hybrid search with citations.

## Scope
pypdf + text splitter; bge-small embeddings into pgvector; vector + full-text search merged by rank fusion; `retrieve(query)` returns chunks with document IDs.

## Related
- [[ADR-004 Postgres with pgvector]]

## Notes
