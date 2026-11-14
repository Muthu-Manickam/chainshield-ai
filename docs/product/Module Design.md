---
type: product
status: proposed
updated: 2026-11-15
source: chosen by Fable 5.2 orchestrator from 6 independent plans (3 Opus 5.5, 3 Fable 5.2)
---
# Module Design (proposed)

6 modules. Winning plan: Fable simplicity plan (88.3/100).

| # | Module | Owns |
|---|---|---|
| 1 | `frontend` | 8 pages, role-based navigation, charts, live investigation and chat |
| 2 | `core` | Login, roles, users, background jobs, audit log, evaluation results |
| 3 | `ml` | Offline training for all models: DataCo pipeline, features, splits, LR/XGBoost, TF-IDF/BiLSTM/DistilBERT, SHAP. Files in, model files out; no DB |
| 4 | `signals` | Serves both models: order risk, incident queue + classification, analyst review, model registry, retrain / promote / rollback |
| 5 | `knowledge` | Document upload, chunking, embeddings, hybrid search, citations, evidence gap; no LLM |
| 6 | `assistant` | LLM client, investigation graph, chatbot, action rules, validator, approvals, cited report |

Dependencies: `assistant → signals, knowledge → core`; `signals → ml`.

## Key decisions
| Question | Decision |
|---|---|
| Chatbot | Second graph inside `assistant`; read-only, no actions |
| Cascade | No; one 5-class DistilBERT; BiLSTM compared, screening errors reported offline |
| Retraining | In `signals`; promotion set, gate, admin promote/rollback; sealed test scored once |
| Incident-to-order link | None; analyst picks scope, labelled "not linked by data" |
| Dashboards | Not a module; each module exposes `/stats` |
| Approval | Status change, then a second task writes the report (no checkpointer) |

Untuned defaults to revisit: 60/10/15/15 split, 15% queue pool, 0.005 promotion margin.

## Related
- [[Alignment with Proposal and Tracker]]
- [[Product Overview]]
