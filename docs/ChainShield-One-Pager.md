# ChainShield AI: one-page overview

**What it is.** An internal web app for a logistics operations team. It predicts which orders are likely to arrive late, screens disaster reports for the few that matter, finds the right procedure in guidance documents, and has AI agents propose cited, rule-checked actions that a supervisor approves. Group 12 capstone; v1.0.0, private repo `Muthu-Manickam/chainshield-ai`.

**Who uses it.** Analysts review risk and incidents and start investigations; supervisors approve actions; admins manage users, documents, rules and models. Customers never use it. Orders are historical (DataCo, 2015-2018); incident reports are replayed from a labelled tweet dataset.

## What it does

| Area | How it works | Result |
|---|---|---|
| Order risk (ML) | 62,897 DataCo orders; leaky and personal columns removed; time-based split; Logistic Regression and XGBoost with calibration; SHAP gives the top 5 reasons per order | ROC-AUC 0.746 vs 0.739 for shipping mode alone |
| Incident triage (DL + NLP) | CrisisMMD tweets, 5 humanitarian classes (infrastructure, affected people, rescue, other, not humanitarian); TF-IDF vs BiLSTM vs DistilBERT; low-confidence reports go to review | Macro-F1 0.633 / 0.551 / 0.638; unseen-event test 0.572 |
| Guidance search (RAG) | 18 documents (FEMA, FHWA, WFP Logistics Cluster, IFRC, 8 team SOPs) chunked and embedded (bge-small) in Postgres pgvector; vector + keyword search; citation keys like `SOP-03#5`; "evidence gap" when nothing fits | Recall@5 0.90, gap detection 0.88 on 60 questions |
| Investigation agents | LangGraph: intake, Intelligence agent (findings), Knowledge agent (cited guidance), Planning agent (ranks only rule-allowed actions), code validator (citations, numbers, no causal claims), one retry then template | Supervisor approves or rejects each action; cited report with disclaimer |
| Chatbot | Tool-using LangGraph agent with 8 read-only tools (orders, incidents, guidance, investigations, models); same validator | Cited answers; never takes actions |
| Retraining | Analyst corrections and released data batches; retrain in a background job; gate vs champion on a promotion set; admin promotes or rolls back; every step audited | DistilBERT promotion shows a failed-gate override |

**Pages.** Overview, Orders, Incidents, Investigations, Assistant, Knowledge, Models, Admin, each shown by role.

## How it is built

| Layer | Choice |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind, shadcn/ui, Recharts |
| Backend | FastAPI, Pydantic, SQLAlchemy, Alembic; login with JWT cookie and 3 roles |
| Database | PostgreSQL 18 + pgvector (vectors and full-text search in one place) |
| ML | scikit-learn, XGBoost, SHAP, PyTorch, Hugging Face Transformers, sentence-transformers |
| Agents and LLM | LangGraph; OpenRouter `gpt-6-luna` with `claude-haiku-5.5` fallback; responses cached; $3 budget cap; offline replay mode |
| Run | `docker compose up --build`, then http://localhost:18080 (db, api, web) |

**Modules (6).** `frontend`, `core` (auth, jobs, audit), `ml` (training), `signals` (order risk, incidents, model registry), `knowledge` (RAG), `assistant` (agents, chatbot, rules, validator).

**Quality.** 107 backend and 6 ML tests, a role test over all 34 routes, lint and type checks clean; full journeys verified in a browser on a fresh database. About 5,600 lines of code after a review pass removed about 720.

## Honest limits

Incidents are not linked to orders by data (the analyst picks the order scope, and the app says so). Data is historical and the incident feed is replayed, not live. The risk model mostly learns shipping mode. The investigation is a fixed pipeline of agent steps, while the chatbot chooses its own tools. People make every decision.
