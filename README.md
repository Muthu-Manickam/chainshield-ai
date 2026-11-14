# ChainShield AI

An internal web app for a logistics team. It predicts late-delivery risk for orders, screens and classifies
disaster reports, answers questions from cited guidance (RAG), runs multi-agent investigations that need
supervisor approval, offers a chatbot, and lets admins retrain and promote models.

## Run it

```
cp .env.example .env     # only if .env does not exist; LLM keys are optional (see offline demo)
docker compose up --build
```

Then open <http://localhost:18080>.

| Service | Host port | Notes |
|---|---|---|
| web (UI) | 18080 | proxies `/api` to the api container |
| api (FastAPI) | 18800 | docs at <http://localhost:18800/docs> |
| db (Postgres + pgvector) | not published | reachable only inside Compose |

The api container runs migrations and the idempotent seed on start.

## Demo users

Password for all three: `chainshield`

| Email | Role | Can do |
|---|---|---|
| `analyst@chainshield.local` | analyst | browse orders, review incidents, start investigations, chat |
| `supervisor@chainshield.local` | supervisor | everything an analyst can, plus approve or reject actions |
| `admin@chainshield.local` | admin | everything, plus users, rules, documents, retrain and promote |

## Retrain and promote (UI)

Sign in as admin, open **Models**:

1. Release a batch of orders or incidents for training.
2. Pick a task and model family, then **Retrain**. A job runs and a candidate version appears.
3. Compare the candidate with the champion, then **Promote** it if the gate passes.

## Offline demo

Set `LLM_MODE=replay` in `.env`. The assistant then serves only cached LLM responses, so no network or API key
is needed and no cost is incurred.

## Tests

```
cd backend && uv run pytest -q
```

Tests use their own database (`cs_<task>`) and empty every table after each test. Never point `DATABASE_URL`
at the main `chainshield` database.

## Where decisions live

- `CLAUDE.md`: coding rules and every locked decision (data, ML, RAG, retraining, ports).
- `docs/`: product overview, module design, ADRs. Open the folder in Obsidian, start at `docs/Home.md`.
- `STACK.lock.md`: pinned stack versions.
