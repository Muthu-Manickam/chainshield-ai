---
type: index
---
# Tech stack decisions

| ID | Decision | Status |
|---|---|---|
| [[ADR-001 Simple stack]] | Use a deliberately small stack: React + TypeScript (Vite), FastAPI, Postgres + pgvector. | accepted |
| [[ADR-002 React with Vite]] | Frontend is React 19 + TypeScript 5.9 built with Vite 8, styled with Tailwind 4 and shadcn/ui. | accepted |
| [[ADR-003 Single Python backend]] | All business logic, ML inference and agents live in one FastAPI app. | accepted |
| [[ADR-004 Postgres with pgvector]] | One database: PostgreSQL 18 with pgvector 0.8.7, run in Docker. | accepted |
| [[ADR-005 Auth in FastAPI]] | Email + password auth owned by FastAPI with three roles. | accepted |
| [[ADR-006 Keep proposal models]] | Keep XGBoost, BiLSTM and DistilBERT as named in the proposal. | accepted |
| [[ADR-007 LangGraph and OpenRouter]] | Agents use LangGraph 1.2; LLM calls go to OpenRouter through langchain-openai. | accepted |
| [[ADR-008 TypeScript 5.9]] | Pin TypeScript 5.9.3, not 7.x. | accepted |
| [[ADR-009 Code and UI principles]] | Modern, single-theme UI and minimal, human-written code, kept lean by two mid-build checkpoints and one final review-and-removal pass. | accepted |
