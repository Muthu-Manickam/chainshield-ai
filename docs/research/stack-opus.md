# ChainShield: stack and database choice (from first principles)

Versions and licences were checked on PyPI (`https://pypi.org/project/<name>/`) on 15 Nov 2026. Pin them exactly in `uv.lock`.

## 1. Summary

One Python 3.12 codebase, managed with uv, runs entirely on a laptop. Orders are processed with pandas and stored as Parquet. LightGBM predicts late delivery and SHAP explains each prediction. The tweet task compares TF-IDF + logistic regression, a PyTorch BiGRU and a fine-tuned DistilRoBERTa, with the GRU and transformer trained on Kaggle GPUs. The corpus is parsed once with Docling, embedded locally with bge-small, and searched with SQLite FTS5 (BM25) plus exact NumPy cosine similarity. No vector database is needed. The agent workflow is a plain-Python pipeline of Pydantic AI agents with typed outputs, a fallback model and a response cache. All results and traces go into one SQLite file, which the Streamlit dashboard reads. OpenAI gpt-5-mini is the primary LLM and Gemma 4 on Ollama is the local fallback. The demo replays cached responses, so it runs offline and deterministically.

## 2. Stack table

| Layer | Choice | Why | Alternative rejected and why |
|---|---|---|---|
| Language/runtime | Python 3.12 | All required ML libraries; XGBoost 3.4 and SHAP 0.54 need ≥3.12 | TypeScript: no tabular ML or fine-tuning ecosystem |
| Env/packaging | uv 0.13 + `uv.lock` | Installs Python and dependencies reproducibly on macOS and Windows | conda: slow, no true lockfile |
| Data processing | pandas 3.1 → Parquet; DuckDB 2.0 only for notebook SQL | Matches the scikit-learn and SHAP APIs; 96 MB fits in memory | Polars 2.1: a second API with no speed problem to solve |
| Tabular ML + explainability | LightGBM 4.7 + SHAP `TreeExplainer`; logistic-regression baseline | Fast on CPU, native categoricals, exact per-order SHAP values | XGBoost/CatBoost: no advantage here; deep tabular models are harder to explain |
| Text: classical | scikit-learn 1.9 TF-IDF (word + char n-grams) + LogisticRegression | Strong, transparent baseline; trains in seconds | Naive Bayes: usually weaker |
| Text: recurrent | PyTorch 2.15 BiGRU with GloVe-Twitter vectors | Same framework as the transformer; the training loop is visible | Keras 3: a second DL framework for one model |
| Text: transformer | HF transformers 5.23 `Trainer`, `distilroberta-base` (82M) | Under 30 min on a T4; CPU inference on a laptop | BERTweet/ModernBERT: marginal gain, heavier or fussier tokenisation |
| Training environment | Kaggle Notebooks (~30 GPU-h/week, 12 h sessions, [source](https://www.spheron.network/blog/google-colab-alternatives-8-gpu-clouds-compared-2026/)) with a **private** dataset; Colab as backup | Predictable quota; private datasets respect the tweet licence | Paid cloud GPUs: outside the budget |
| Embeddings | sentence-transformers 6.3 + `BAAI/bge-small-en-v1.5` (MIT, 384-dim, [card](https://huggingface.co/cstr/bge-small-en-v1.5-GGUF)) | Free, offline, fast on CPU | API embeddings: cost money, need network, and the vectors change if the provider changes the model |
| Vector search | Exact cosine in NumPy + [FTS5](https://sqlite.org/fts5.html) BM25, fused with reciprocal rank fusion | Scanning 300×384 vectors takes microseconds; exact search removes ANN error from the evaluation | Chroma/LanceDB/FAISS: an extra store to sync for a scale problem the project does not have |
| Document parsing | Docling 2.150 (MIT), run once at build time, with `HybridChunker` ([docs](https://github.com/docling-project/docling/blob/main/docs/concepts/chunking.md)) | Handles PDF and HTML, keeps headings, tables and page numbers for citations | PyMuPDF: AGPL. pypdf: loses document structure |
| Agent orchestration | Plain Python sequence: intelligence → knowledge → planning → rule check → report; each role is a Pydantic AI `Agent` | Deterministic, testable, easy to explain | LangGraph 1.2: graph and checkpoint machinery a linear flow doesn't need. CrewAI: autonomous delegation is non-reproducible |
| LLM provider + client | OpenAI `gpt-5-mini` ($0.25/$2 per M tokens, [pricing](https://models.litellm.ai/models/gpt-5-mini)) via Pydantic AI 2.68; `FallbackModel` ([docs](https://pydantic.dev/docs/ai/api/models/fallback/)) switches to [Gemma 4 E4B on Ollama](https://ollama.com/library/gemma4) | About $0.02 per investigation; API data is not used for training by default ([policy](https://openai.com/policies/api-data-usage-policies)) | Gemini free tier: about 20 requests/day on Flash ([limits](https://www.scriptbyai.com/gemini-api-free-tier-limits/)), and free-tier prompts may be used to improve Google products ([billing](https://ai.google.dev/gemini-api/docs/billing)), which conflicts with the tweet licence |
| Structured output/validation | Pydantic 2.14 models as `output_type`; cost and approval rules as pure Python functions | Invalid output triggers a retry or the fallback; rule decisions are auditable code, not LLM judgement | Instructor: duplicates Pydantic AI |
| Caching | `llm_cache` table keyed by SHA-256 of model, messages, schema and parameters; embeddings cached by chunk hash | Enables offline replay, free reruns and identical outputs | diskcache: a second store to ship |
| Observability/tracing | Own `run_step` table, shown on a dashboard page | Run logs are a deliverable, so they live in the app's own data | Langfuse: self-hosting needs Postgres, ClickHouse, Redis and S3 ([guide](https://docs.railway.com/guides/langfuse-llm-observability)). LangSmith: SaaS, data leaves the laptop |
| App/UI | Streamlit 1.67 multipage app | Five pages in pure Python by one developer | FastAPI + React: two codebases. Gradio: suited to single-model demos |
| Testing/quality | pytest 9.2, ruff 0.17, Pydantic AI `TestModel` ([guide](https://pydantic.dev/docs/ai/guides/testing)), golden outputs for scripted scenarios | Tests need no network or API key; run in GitHub Actions on fixture data | Strict mypy across the whole codebase: too costly in 8 weeks |
| Artifact/data storage | `data/raw` (git-ignored, SHA-256 manifest); `artifacts/<model>/<run_id>/`; weights in a **private** Hugging Face repo | Simple, versioned by run ID, no server | MLflow 3.18: a second UI that duplicates the model-comparison page. DVC: setup cost exceeds the benefit |
| Deployment/demo | `uv sync && uv run chainshield fetch && uv run chainshield demo --replay` | Works from a fresh clone with no network or API key | Docker: torch image >5 GB and fragile on Windows. Public hosting: forbidden by the tweet licence |

## 3. Database

**Database: one SQLite file (`chainshield.db`, WAL mode) with built-in FTS5. No separate vector database.**

SQLite needs no server, ships with Python, and in WAL mode lets the agent CLI write while Streamlit reads. I rejected DuckDB as the app database because only one process can hold a DuckDB file open for writing ([docs](https://duckdb.org/docs/1.5/connect/concurrency)), and the app's workload is small transactional updates. I rejected Postgres + pgvector because it adds a server to every laptop for under 1 GB of data.

**Files** hold the immutable, bulky inputs: raw CSV, tweets, PDFs, cleaned Parquet, model weights and plots. **The database** holds everything the app queries, joins or updates.

```sql
orders_scored(order_id PK, order_date, region, ship_mode, p_late, label, model_run_id, top_shap_json)
tweets_classified(tweet_id PK, event, informative, info_p, category, cat_p, model_run_id)
model_run(run_id PK, task, model_name, split, params_json, metrics_json, artifact_path, created_at)
document(doc_id PK, title, source_url, sha256, licence)
chunk(chunk_id PK, doc_id FK, ord, page, heading_path, text, embedding BLOB, embed_model)
chunk_fts            -- FTS5 virtual table, content='chunk'
incident(incident_id PK, source, source_ref, severity, status, created_at)        -- review queue
agent_run(run_id PK, incident_id FK, scenario, mode, config_hash, status, report_md, cost_usd)
run_step(step_id PK, run_id FK, seq, role, kind, input_json, output_json, model,
         tokens_in, tokens_out, latency_ms, error)
citation(run_id FK, step_id FK, chunk_id FK, score)
rule_check(run_id FK, action_json, rule_id, passed, reason)
llm_cache(key PK, model, request_json, response_json, created_at)
eval_result(eval_id PK, suite, variant, metric, value, n)                           -- ablations by variant
```

**How vectors and relational data relate.** Each embedding is stored in its `chunk` row. At startup the retriever loads all embeddings into a NumPy matrix of about 0.5 MB. A query is scored against every chunk with cosine similarity and with FTS5 `bm25()`, and the two rankings are fused with reciprocal rank fusion. The resulting `chunk_id`s join directly to `document` for citations. A `citation` row records which chunk supported which agent step. Because there is one ID space, nothing can drift out of sync. If the corpus grew past roughly 100k chunks, sqlite-vec or LanceDB could go behind the same retriever interface.

## 4. Deliberately not used

- **LangChain/LlamaIndex**: abstraction and API churn over what is a 50-line retriever.
- **LiteLLM**: two compromised PyPI releases in 2026 ([March](https://securitylabs.datadoghq.com/articles/litellm-compromised-pypi-teampcp-supply-chain-campaign/), [October](https://docs.litellm.ai/blog/security-incident-oct-21-2026-attack-chain)), and Pydantic AI already switches providers.
- **Hosted vector databases**: an account and a network dependency with no benefit at this size.
- **CrewAI/AutoGen**: autonomous delegation works against the reproducibility requirement.
- **PyMuPDF**: AGPL licence.
- **Docker as the primary path, or cloud deployment**: adds risk to the demo with no audience to justify it.
- **LLM-as-judge as the main RAG metric (Ragas)**: recall@k and MRR on about 50 hand-labelled questions are cheaper and easier to defend. An LLM judge can be reported as a secondary metric.

## 5. Top 3 risks and mitigations

1. **Label leakage in the order model.** Datasets of this shape usually include post-shipment fields such as actual shipping days and delivery status, which reveal the label.
   - Use an allow-list of fields known at order time.
   - Split by time (train 2015–2017, test 2018).
   - Add a test that fails if a banned column reaches the model.
2. **LLM outage or invalid output during the demo.**
   - Pydantic retries come first, then `FallbackModel` switches to Ollama.
   - The demo defaults to `--replay`.
   - Errors are logged to `run_step.error`, and the run continues with a "degraded" flag.
   - Scripted scenarios are checked against golden outputs in CI.
3. **Tweet licence leak, or a fresh clone that doesn't reproduce.**
   - Data and weights stay out of git and come from private Kaggle and Hugging Face sources through `fetch`, with checksums.
   - CPU-only torch is pinned in `uv.lock`.
   - Pre-parsed chunks and embeddings ship in the database, so Docling isn't needed at demo time.
   - A CI job tests a fresh clone on macOS and Windows.
