# CLAUDE.md: ChainShield AI

Every agent reads this file first. It holds the decisions all code must follow. If you make a decision other agents
need, add it to the right section in your branch and list it in your hand-back. Do not delete others' entries.

ChainShield AI is an internal web app for a logistics team: order late-risk prediction, disaster-report screening
and classification, cited guidance search (RAG), multi-agent investigations with approvals, a chatbot, and
retraining. Details: `docs/product/Product Overview.md`.

## 1. Read before coding
- Folder and file layout (locked): `docs/Code Structure.md`. Create only the files listed there.
- Stack and versions (locked): `STACK.lock.md`.
- Modules: `docs/product/Module Design.md`.

## 2. Code rules
- Minimal code, written like a careful human. Clear names, short functions (~40 lines), files under ~300 lines.
- No function, component or file unless something uses it now. No duplicate logic. No utils/helpers/base/factory.
- Backend: `router.py` (HTTP only) → plain service functions → `models.py`. Modules call each other only through
  service functions. Direction: `assistant → signals, knowledge → core`; `signals → ml`. `ml` never imports `backend`.
- Frontend: one file per page, TanStack Query + shadcn/ui, light theme only, modern clean look, no extra libraries.
- No new library without a reason written in your hand-back.

## 3. Git workflow
- Branch `task/<task-id>-<short-name>` from `release/v1`; commit only files your task owns.
- A task that depends on another branches only after that task is merged into `release/v1`.
- Shared files (`app/main.py`, `App.tsx`, `AppShell.tsx`, `types.ts`, `docker-compose.yml`) come from the skeleton
  task; edit only your own lines. Migrations: add a new revision, never edit an old one.
- Run your task's acceptance check before hand-back. Do not run `docker compose up` (orchestrator only).

## 4. Data and ML decisions (DataCo, order risk)
- Source: `data/raw/dataco/DataCoSupplyChainDataset.csv` (180,519 rows → 65,752 orders).
- Aggregate item rows to one row per `Order Id`. Drop `CANCELED` and `SUSPECTED_FRAUD` orders (2,855).
- Label: `Late_delivery_risk`. Prediction time = order creation.
- Banned features (leak or PII): `Days for shipping (real)`, `Delivery Status`, `Order Status`, `shipping date`,
  `Type`, `Benefit per order`, `Order Profit Per Order`, `Order Item Profit Ratio`, customer email/password/names/street.
  `ml/tests/test_features.py` asserts allowlist ∩ banned = ∅.
- Split by order date into blocks: train 60%, validation 10%, stream 15% (S1, S2, S3), test 15%.
  Validation fits calibration and thresholds. S1/S2 are released for retraining. S3 is the promotion set.
  Test is scored once at freeze. Report the market mix of each block.
- Models: majority + shipping-mode rule baselines, Logistic Regression, XGBoost, isotonic calibration.
  SHAP top-5 factors per order. Metrics: ROC-AUC, PR-AUC, F1, Brier. Expected ROC-AUC 0.75-0.78; above 0.85 = leakage alarm.

## 5. NLP decisions (CrisisMMD)
- Source: `data/raw/crisismmd/events/*.tsv` (use `label_text`, not the image label) and
  `data/raw/crisismmd/splits/` (official split, ~11,584 / 2,237 / 2,237 tweets after dedupe by tweet id).
- Humanitarian classes merged 8 → 5:
  `infrastructure_and_utility_damage` + `vehicle_damage` → `infrastructure`;
  `affected_individuals` + `injured_or_dead_people` + `missing_or_found_people` → `affected_people`;
  `rescue_volunteering_or_donation_effort` → `rescue_donation`; `other_relevant_information` → `other_relevant`;
  `not_humanitarian` → `not_humanitarian`.
- Queue pool: 15% of the train split held out (stratified by event and class) and never trained on; it feeds the
  incident queue. 20% of the pool is the incident promotion holdout.
- Models compared: TF-IDF + Logistic Regression, BiLSTM (PyTorch), DistilBERT (`distilbert-base-uncased`).
  Report macro-F1, per-class recall, confusion matrix; leave-one-event-out for TF-IDF and BiLSTM.
- Served: one 5-class model (best by macro-F1, expected DistilBERT; TF-IDF as fallback).
  Screening = `1 − p(not_humanitarian)`. `needs_review` when max confidence < threshold chosen on dev, or < 3 tokens.
  The BiLSTM-screen-then-classify error count is an offline table only.
- India–Nepal corpus: not used in v1.

## 6. RAG decisions
- Embeddings: `BAAI/bge-small-en-v1.5`, 384-dim, pgvector HNSW cosine. Keyword: `tsvector` + GIN.
- Chunks: split on headings, then ~350 tokens with 50 overlap. Citation key `<DOC-CODE>#<n>` (e.g. `SOP-03#4`).
- Search: dense top 20 + keyword top 20 → reciprocal rank fusion → top 5.
- Evidence gap: best cosine below a dev-tuned threshold → `evidence_gap=true`; callers must say no guidance found.
- Documents are tagged `public` or `team-authored (illustrative)`.

## 7. Agents and LLM decisions
- Investigation graph: `intake` (code) → `intelligence` (LLM) → `knowledge` (code query + LLM summary) →
  `planning` (rule checker first, LLM ranks eligible actions only) → `validator` (code). Ends at `awaiting_approval`.
  Supervisor decision is a status change that starts `write_report`. No checkpointer.
- Validator rejects: unknown citation keys, actions not in the eligible set, numbers not in tool output, any sentence
  claiming an incident caused a specific order's delay. One retry, then template + `degraded` flag.
- Chat: one LangGraph agent with read-only tools (max 4 tool calls), same validator, never proposes actions.
- LLM: temperature 0, structured output (Pydantic), one retry, then template. Every call cached in `llm_cache`.
  `LLM_MODE=replay` serves cache only (offline demo). Hard budget: $3 total; calls stop when the logged cost reaches it.
- Provider: OpenRouter (owner's personal key) via `langchain-openai` with `base_url` from `Settings`; no `litellm`
  package. Settings: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL=openai/gpt-6-luna`,
  `LLM_FALLBACK_MODEL=anthropic/claude-haiku-5.5`, `LLM_MODE`, `LLM_BUDGET_USD=3`.
- `gpt-6-luna` is a reasoning model: send `reasoning: {effort: "low"}`, no temperature, `max_tokens` ≥ 500
  (smaller limits return empty content). Request `usage: {include: true}` and add `usage.cost` to the budget log.
- Tracing: Langfuse (cloud Hobby tier) via its LangChain callback on every graph run and LLM call, enabled when
  `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` are set. `investigation_steps` stays the app's own record.

## 8. Retraining decisions
- Trigger: admin button on the Models page (badge at 200 new reviews or a released S-batch). No scheduler.
- A `core/jobs.py` job runs `python -m ml train ...` as a subprocess; artifacts to `artifacts/<task>/v<n>/`.
- Compare candidate vs champion on the promotion set (never the test set). Gate: primary metric no more than 0.005
  below champion, infrastructure recall not lower, Brier not worse, no leakage alarm.
- Admin promotes; champion hot-reloads; rollback = promote an older version. Every score stores its version id.

## 9. Verification
- Merges run only the task's acceptance check. Browser checkpoints: after the skeleton, after real models + RAG,
  and a final full pass with code cleanup. Everything runs via `docker compose up` (db, api, web).

## 10. Decision log (append, newest last)
| Date | Decision | By |
|---|---|---|
| 2026-11-15 | Initial decisions above | orchestrator |
| 2026-11-15 | Host ports 5432 and 8000 are taken: compose publishes db on 55432, api on 18800, web on 18080. Docker images install CPU-only torch (`--index-url https://download.pytorch.org/whl/cpu`). RAG documents live in `corpus/` (SOPs, sources, questions) and `data/corpus/public/` (downloads). | orchestrator |
| 2026-11-15 | LLM provider: OpenRouter, gpt-6-luna primary, claude-haiku-5.5 fallback, $3 app budget | owner |
| 2026-11-15 | Tweet split = `informative_{train,dev,test}.json` tweet ids (cover all 16,058 tweets, 11,584/2,237/2,237). The `humanitarian_*` split files assign different tweets and carry image-level labels, so they are not used. Labels come from the TSV `text_info` / `text_human` columns; a tweet in several events keeps its first row. Pool holdout is stratified by category only (event+category strata are too small inside the pool). | ML1 |
| 2026-11-15 | `orders.parquet`: one row per order sorted by date; `order_value` = sum of `Order Item Total`, `item_count` = sum of quantity, `top_category` = category of the highest-value line. Blocks have very different market mixes (s1 all LATAM, s3 all Europe, test Europe + Pacific Asia); this comes from the DataCo dates. | ML1 |
| 2026-11-15 | Risk artifacts: `artifacts/risk/v<n>/{model.joblib, metadata.json, metrics.json}`. `metadata.json` has `task`, `family` (`risk_logreg`/`risk_xgboost`), `classes` [0,1], `features`, `categories`, `threshold`. `Predictor.load(dir)`, then `predict_proba(df)` takes raw order rows (orders.parquet columns) and returns an (n,2) array; `explain(df, top=5)` returns per row `[("shipping_mode=Second Class", 0.08), ...]` as SHAP log-odds summed per source feature. Served model = best val PR-AUC of the two calibrated candidates. F1 uses the threshold that maximises val F1. | ML1 |
| 2026-11-15 | Env `CHAINSHIELD_DATA_DIR` / `CHAINSHIELD_ARTIFACTS_DIR` are read by `ml.data.data_dir()` / `artifacts_dir()`. CLI: `python -m ml prepare [orders\|tweets]`; `train risk --version N [--extra s1,s2]`; `evaluate risk --version N --final`; `train text --family F --version N [--extra-labels PATH]`; `evaluate text --family F --version N [--final]`. macOS needs `brew install libomp` for xgboost (slim Linux images may need `libgomp1`). | ML1 |
