---
type: standard
status: locked
updated: 2026-11-15
---
# Code Structure (every sub-agent follows this)

This is the only allowed layout for v1. Agents do not invent folders or files. If a task truly needs a file that
is not listed here, the agent names it in its hand-back; the orchestrator decides and updates this note.

## 1. Repo layout

```
chainshield-ai/
  docker-compose.yml        db + api + web
  .env.example              DATABASE_URL, JWT_SECRET, OPENROUTER_API_KEY, LLM_MODE
  pyproject.toml            uv workspace: members backend, ml
  backend/                  FastAPI app (serving, API, agents)
  ml/                       offline training package (no DB, no web)
  frontend/                 React app
  data/                     git-ignored: raw/, processed/
  artifacts/                git-ignored: <task>/v<n>/ model files + metrics.json
  docs/                     this Obsidian vault
```

## 2. Backend (`backend/`)

```
backend/
  Dockerfile
  pyproject.toml
  alembic.ini
  migrations/
    env.py
    versions/               one file per revision: <nnnn>_<task-id>_<what>.py
  app/
    main.py                 create FastAPI app, include the 4 module routers, nothing else
    seed.py                 demo users (one per role), action rules, sample incidents
    core/
      config.py             Settings (pydantic-settings), the only place env vars are read
      db.py                 engine, SessionLocal, Base, get_db dependency
      auth.py               password hashing, JWT cookie, current_user, require_role
      jobs.py               run a function as a tracked background job
      models.py             users, jobs, audit_log, eval_runs
      schemas.py
      router.py             /api/auth/*, /api/users/*, /api/jobs/*, /api/evals
    signals/
      orders.py             order queries, batch scoring, SHAP factors, stats
      incidents.py          queue, classify on arrival, review, stats
      registry.py           model versions, load champion, retrain job, compare, promote, rollback
      models.py             orders, incidents, model_versions
      schemas.py
      router.py             /api/orders/*, /api/incidents/*, /api/models/*
    knowledge/
      ingest.py             pdf/markdown → chunks → embeddings → db
      search.py             hybrid search (pgvector + tsvector, rank fusion), evidence gap
      models.py             documents, chunks
      schemas.py
      router.py             /api/knowledge/*
    assistant/
      llm.py                OpenRouter client: structured output, retry, fallback, llm_cache, replay mode
      tools.py              read-only tools shared by investigation and chat
      rules.py              action rule checker (pure Python)
      validator.py          citations, numbers, eligible actions, no causal claim
      investigation.py      LangGraph investigation graph + report writer
      chat.py               LangGraph chat graph
      models.py             action_rules, investigations, investigation_steps, investigation_actions,
                            chat_messages, llm_cache
      schemas.py
      router.py             /api/investigations/*, /api/chat/*, /api/rules/*
  tests/
    conftest.py             test db + client + login helpers
    test_core.py
    test_signals.py
    test_knowledge.py
    test_assistant.py
```

## 3. ML (`ml/`)

```
ml/
  pyproject.toml
  ml/
    __main__.py             CLI: python -m ml prepare | train | evaluate  (same command locally, Colab, in-app)
    data.py                 DataCo → orders table + blocks; CrisisMMD → texts, labels, pool, splits
    features.py             order feature allowlist + banned list; text cleaning (shared by train and serve)
    risk.py                 baselines, Logistic Regression, XGBoost, calibration, SHAP, metrics
    text.py                 TF-IDF, BiLSTM, DistilBERT: train, evaluate, event-held-out folds
    predictor.py            Predictor: load(path), predict_proba(x), explain(x)
  tests/
    test_features.py        leakage test (allowlist ∩ banned = ∅), split sanity
    test_predictor.py
```

## 4. Frontend (`frontend/`)

```
frontend/
  Dockerfile
  package.json  vite.config.ts  tsconfig.json  index.html  components.json
  src/
    main.tsx                React root, QueryClient, router
    App.tsx                 routes + role guard
    api.ts                  one api() fetch helper (cookie auth, JSON, errors) + stream() for SSE
    types.ts                TypeScript types mirroring backend schemas
    index.css               Tailwind + shadcn tokens (light theme only)
    components/
      ui/                   shadcn components, added only when used (button, card, table, badge, input,
                            dialog, tabs, select, textarea, sonner, chart, skeleton)
      AppShell.tsx          sidebar + header
      StatCard.tsx          KPI card (used on several pages)
    pages/
      Login.tsx  Overview.tsx  Orders.tsx  Incidents.tsx  Investigations.tsx
      Assistant.tsx  Knowledge.tsx  Models.tsx  Admin.tsx
```

## 5. Patterns

**Backend**
- Layering inside a module: `router.py` (HTTP only) → service files (plain functions) → `models.py`.
- Service code is plain functions, not classes. Classes only for SQLAlchemy models, Pydantic schemas, and
  `Predictor`.
- Modules call each other only through their service functions, never another module's router or tables directly.
  Allowed direction: `assistant → signals, knowledge → core`; `signals → ml`.
- Dependencies injected only for the DB session (`get_db`) and the user (`current_user`, `require_role`).
- Routers raise `HTTPException`; services return values or `None` and raise `ValueError` for bad input.
- SQLAlchemy 2.x typed `Mapped[...]`, sync sessions. Pydantic v2 schemas with `from_attributes=True`.
- REST under `/api/<area>/...`; JSON in and out; streams use `text/event-stream`.
- Background work goes through `core/jobs.py` only.

**Frontend**
- One file per page. A page fetches with `useQuery` / `useMutation` and renders shadcn components.
- No state library, no form library, no table library. Local `useState` only.
- A component moves to `components/` only when a second page needs it.
- All HTTP calls go through `api.ts`. Types live in `types.ts`.
- Light theme, shadcn defaults, Tailwind utility classes; no custom CSS beyond `index.css`.

**ML**
- Functions over classes; one `Predictor` class is the only shared interface.
- Inputs are files in `data/`; outputs are `artifacts/<task>/v<n>/` with `model.*` and `metrics.json`.
- The `ml` package never imports from `backend`.

## 6. Naming and size

| Thing | Rule |
|---|---|
| Python | `snake_case` functions and files, `PascalCase` classes, nouns for files, verbs for functions |
| TypeScript | `PascalCase` components and page files, `camelCase` functions and variables |
| DB | plural `snake_case` tables, `id` primary key, `<table>_id` foreign keys, `created_at` on every table |
| API | plural nouns: `/api/orders/{id}`, actions as sub-paths: `/api/models/{id}/promote` |
| Branches | `task/<task-id>-<short-name>` from `release/v1` |
| Size | functions about 40 lines max; files about 300 lines max; split only when a file passes that |

## 7. Shared files (conflict rules)

| File | Rule |
|---|---|
| `app/main.py`, `App.tsx`, `AppShell.tsx`, `types.ts`, `docker-compose.yml` | Written once by the skeleton task with every route, page and type stubbed. Later tasks edit only their own lines. |
| `migrations/versions/` | Skeleton task creates all v1 tables in one revision. Later changes add a new revision file; never edit an old one. |
| `seed.py` | Each task appends only its own clearly marked function. |
| `components/ui/` | Added with the shadcn CLI only; never hand-edited. |

## 8. What not to create

No `utils.py`, `helpers.py`, `common/`, `base.py`, `services/` folders, `hooks/` folders, barrel `index.ts`
files, wrapper classes, factories, abstract interfaces, config objects beyond `Settings`, or per-function files.
No README per folder. No comments that repeat the code.

## Related
- [[Tech Stack]]
- [[ADR-009 Code and UI principles]]
- [[Module Design]]
