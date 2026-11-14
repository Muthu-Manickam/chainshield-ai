---
type: stack
status: locked
locked: 2026-11-15
---
# Tech Stack

Locked 2026-11-15. Versions checked live on npm, PyPI and Docker Hub. Pin exactly.
Rule: add a library only when the code would be clearly longer or worse without it.

## Architecture

```
frontend (React + TypeScript, Vite)  ──REST/stream──>  backend (FastAPI, Python)  ──>  Postgres + pgvector
                                                            ├─ ML models (loaded at startup)
                                                            ├─ LangGraph agents
                                                            └─ OpenRouter (LLM)
```

## Repo

```
chainshield/
  frontend/          React + TypeScript (Vite)
  backend/           FastAPI app, ML inference, agents, migrations
  ml/                training notebooks/scripts (Colab/Kaggle)
  docker-compose.yml db (Postgres + pgvector), api (FastAPI), web (React build served by Vite preview)
  data/ artifacts/   git-ignored (datasets, model weights)
```

No monorepo tooling: two folders, npm for frontend, uv for backend.

## Frontend

| Purpose | Package | Version |
|---|---|---|
| Build/dev server | `vite` + `@vitejs/plugin-react` | 8.3.8 / 6.3.0 |
| UI | `react`, `react-dom` | 19.3.1 |
| Language | `typescript` | 5.9.3 |
| Styling | `tailwindcss` + `@tailwindcss/vite` | 4.3.5 |
| Components | shadcn/ui (copied into `src/components/ui`) | CLI 4.23.0 |
| Icons | `lucide-react` (comes with shadcn) | 1.73.0 |
| Charts | `recharts` (shadcn chart) | 3.10.1 |
| Routing | `react-router` | 8.5.1 |
| Data fetching | `@tanstack/react-query` | 5.107.1 |

Runs on Node 22.12 (already installed). npm, no pnpm.

## Backend

| Purpose | Package | Version |
|---|---|---|
| Language | Python | 3.12 (via uv) |
| API | `fastapi`, `uvicorn` | 0.163.0 / 0.54.0 |
| Settings, validation | `pydantic`, `pydantic-settings` | 2.14.3 / 2.16.3 |
| Database | `sqlalchemy` (sync), `psycopg[binary]`, `alembic`, `pgvector` | 2.1.8 / 3.3.9 / 1.20.1 / 0.5.1 |
| Uploads, tests | `python-multipart`, `httpx` (tests only) | 0.0.33 / 0.28.1 |
| Auth | `pwdlib[argon2]`, `pyjwt` | 0.4.0 / 2.15.1 |

Auth: email + password, JWT in an httpOnly cookie, roles `analyst`, `supervisor`, `admin`.
Agent runs: FastAPI `BackgroundTasks`; steps saved to Postgres; live progress via `StreamingResponse`.

## Database

PostgreSQL 18 + pgvector 0.8.7 (`pgvector/pgvector:0.8.7-pg18`). Embeddings in a `vector(384)` column with an
HNSW index. Keyword search with Postgres full-text (`tsvector`). LLM cache is a table.

## ML and AI

| Purpose | Package | Version |
|---|---|---|
| Data | `pandas` | 3.1.1 |
| Classical ML, TF-IDF | `scikit-learn` | 1.9.1 |
| Order risk | `xgboost` + `shap` | 3.4.1 / 0.54.1 |
| BiLSTM | `torch` | 2.15.0 |
| DistilBERT | `transformers`, `datasets` | 5.23.0 / 5.2.0 |
| Embeddings | `sentence-transformers` (`BAAI/bge-small-en-v1.5`) | 6.3.0 |
| PDF text | `pypdf` | 7.1.0 |
| Agents | `langgraph` | 1.2.22 |
| LLM client | `langchain-openai` → OpenRouter | 1.8.0 |
| LLM models | OpenRouter: `openai/gpt-6-luna` ($0.10/$0.50 per M), fallback `anthropic/claude-haiku-5.5`; app budget $3 | |
| Tracing | `langfuse` (cloud Hobby, LangChain callback) | 5.2.0 |

## Dev tools

`ruff` 0.17.5 and `pytest` 9.2.0 for the backend. TypeScript compiler checks the frontend.

## Not used

Next.js, Turborepo, pnpm, Redis, Celery, separate vector DB, MLflow, LangSmith, form/validation libraries,
table libraries, codegen, E2E test frameworks, CI pipelines, cloud hosting.
Add any of them later only if a real need appears.
