---
type: product
status: agreed
updated: 2026-11-15
---
# Alignment with Proposal and Tracker

Our design is the same project as the Group 12 proposal (PDF) and the team tracker (XLSX): it keeps their promises,
changes what reviews found risky, and adds the product layer.

## Proposal capabilities
| # | Proposal | Our design | Status |
|---|---|---|---|
| F1 | Shipment risk, LR + XGBoost | Same, with SHAP reasons | Same |
| F2 | BiLSTM screening | BiLSTM trained and compared; live screening from DistilBERT; BiLSTM screening errors in an offline table | Changed |
| F3 | DistilBERT disaster type + humanitarian | Humanitarian same; disaster type from source event, not predicted | Changed |
| F4 | RAG with FAISS + LangChain | Same idea; vectors in pgvector | Same idea |
| F5 | LangGraph Intelligence, Knowledge, Planning | Same, plus validator | Same |
| F6* | Scenario mitigation planning | Rule checker (allowed / rejected) + supervisor approval | Same |
| F7* | Explainable AI + generated reports | SHAP + cited report | Same |
| F8 | Streamlit + Plotly dashboard | React + shadcn, 8 pages | Changed |

Datasets: DataCo (same), CrisisMMD (same), India-Nepal (optional, real Nepal tweets only).

## Tracker stories
| Story | Tracker | Our design |
|---|---|---|
| US-01 Risk | Order-level data, leakage checks, time split, baselines, calibration, SHAP | Kept; adds cancelled/fraud exclusion and full leaky-column list |
| US-02 Screening | TF-IDF vs BiLSTM, 7 event folds, cascade evaluation | Kept; cascade offline; official CrisisMMD split instead of 8,369/3,504/4,145 |
| US-03 Classification | India-Nepal prep, 20 held-out models, 19 neural jobs | Reduced to 2 main models + event-held-out folds; India-Nepal optional |
| US-04 RAG | 15-25 sources, stable chunk IDs, Recall@5 ≥ 80%, grounded ≥ 90%, LLM-only vs RAG | Kept; blind questions + human check |
| US-05 Agents | Referenced, missing | Designed: graph, validator, approvals |
| US-06 Scenario planning | Missing | Designed: rule checker + approvals |
| US-07 Reports | Missing | Designed: cited report |
| US-08 App | Pages, 3 journeys, freeze gate, handover | Kept: 8 pages, same 3 journeys, test scored once |

## Added beyond both files
Login + 3 roles + audit log; Postgres + API; chatbot; retraining loop; approval workflow.

## Workstreams → modules
| Workstream | Module |
|---|---|
| WS1 Data Engineering + ML | `ml` + `signals` (orders) |
| WS2 DL + Transformer NLP | `ml` + `signals` (incidents) |
| WS3 RAG + Knowledge | `knowledge` |
| WS4 Agentic + GenAI | `assistant` |
| WS5 App + Integration | `frontend` + `core` |

## Changes to declare to team / supervisor
1. Live screening from DistilBERT, not BiLSTM (proposal allows "compatible prediction components").
2. Disaster type from source event, not predicted.
3. India-Nepal optional.
4. Official CrisisMMD split.
5. React + Postgres/pgvector replace Streamlit + FAISS.

## Related
- [[Product Overview]]
- [[Module Design]]
- [[Tech Stack]]
